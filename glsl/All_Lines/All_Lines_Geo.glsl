layout(lines) in;
layout(triangle_strip, max_vertices = 60) out;

in VERT_OUT {
    float weight;
    float offset;
    vec4 color;
    int rounded;
    mat4 objectMatrix;
} verts[];

// OUTS
out vec2 mTexCoord;
out float alpha;
out vec4 g_color;

// UNIFORMS
uniform mat4 ModelViewProjectionMatrix;
uniform vec2 Viewport;
uniform vec2 Paper;
uniform vec4 camera_coord1;
uniform vec4 camera_coord2; // camera aligned coords 1BU apart in x
uniform int res;
uniform float scale;
uniform float is_camera;

// CONSTANTS
const float PI = 3.1415926;
const float INCH_TO_CM = 2.54;
const float BU_TO_IN = 100.0 / INCH_TO_CM;

// VARS
vec4 vecOffset = vec4(0.0,0.0,verts[0].offset,0.0);
mat4 objectMatrix = verts[0].objectMatrix;

// Compute pt size in ss units
float get_ss_pt(){
    float ss_pt = 6.0;
    if(is_camera==1){
        vec4 camera_proj_1 = ModelViewProjectionMatrix * camera_coord1;
        vec4 camera_proj_2 = ModelViewProjectionMatrix * camera_coord2;

        vec2 cam_ss1 = camera_proj_1.xy / camera_proj_1.w;
        vec2 cam_ss2 = camera_proj_2.xy / camera_proj_1.w;

        vec2 lengthVec = (cam_ss2 - cam_ss1) * Viewport;
        float ss_dist = length(lengthVec) / length(Viewport); // this is 1BU in ss on x
        float ss_inch = ss_dist * BU_TO_IN; // this is 1 in in ss
        ss_pt = ss_inch / 72 * scale;
    }

    return ss_pt;
}

float ss_pt = get_ss_pt();

void main() {
    // Get Vertex Positions (LOCAL SPACE)
    vec4 p1 =  gl_in[0].gl_Position;
    vec4 p2 =  gl_in[1].gl_Position;

    // Get World Space Positions
    vec4 p1_ws = objectMatrix * p1;
    vec4 p2_ws = objectMatrix * p2;

    // Get Clip Space Co-ordinates (with z offset)
    vec4 p1_clip = ModelViewProjectionMatrix * p1_ws + vecOffset;
    vec4 p2_clip = ModelViewProjectionMatrix * p2_ws + vecOffset;

    // Get Direction (accounting for perspective divide and viewport)
    vec2 dir = normalize((p2_clip.xy/p2_clip.w -p1_clip.xy/p1_clip.w) * Viewport);
    // Get Perpindicular vector for offset
    vec2 offset1 = vec2(-dir.y,dir.x) * verts[0].weight/2.0 * ss_pt / Viewport;
    vec2 offset2 = vec2(-dir.y,dir.x) * verts[1].weight/2.0 * ss_pt / Viewport;

    // set rectangel coords
    vec4 coords[4];
    vec2 texCoords[4];
    vec4 colors[4];
    float alphas[4];

    coords[0] = p1_clip + vec4(offset1.xy * p1_clip.w, 0.0, 0.0);
    texCoords[0] = vec2(0,1);
    colors[0] = verts[0].color;
    alphas[0] = 1.0;

    coords[1] = p1_clip - vec4(offset1.xy * p1_clip.w, 0.0, 0.0);
    texCoords[1] = vec2(0,0);
    colors[1] = verts[0].color;
    alphas[1] = 1.0;

    coords[2] = p2_clip + vec4(offset2.xy * p2_clip.w, 0.0, 0.0);
    texCoords[2] = vec2(1,1);
    colors[2] = verts[1].color;
    alphas[2] = 1.0;

    coords[3] = p2_clip - vec4(offset2.xy * p2_clip.w, 0.0, 0.0);
    texCoords[3] = vec2(1,0);
    colors[3] = verts[1].color;
    alphas[3] = 1.0;

    // Point Pass
    
    vec4 centers[2];
    centers[0] = p1_ws;
    centers[1] = p2_ws;

    for (int i = 0; i < 2; ++i) {
        if (verts[i].rounded == 1){
            float radius = verts[i].weight/2.0;
            // Get Center Point
            vec4 pc = centers[i];
            vec4 pc_clip = ModelViewProjectionMatrix * pc + vecOffset;

            // Define Segments
            int segments = 12;

            // Emit Center
            gl_Position = pc_clip;
            mTexCoord = vec2(0.0,0.5);
            EmitVertex();

            for (int j = 0; j <= segments; j++) {
                // Angle between each side in radians
                float ang = PI * 2.0 / float(segments) * float(j);

                // Offset from center of point
                vec2 circle_dir= vec2(cos(ang), -sin(ang));
                vec2 circleOffset = circle_dir * radius* ss_pt / Viewport;
            
                gl_Position = pc_clip + vec4(circleOffset.xy*pc_clip.w, 0.0, 0.0);
                mTexCoord = vec2(i,1.0);
                alpha = 1.0;
                g_color = verts[i].color;
                EmitVertex();

                gl_Position = pc_clip;
                mTexCoord = vec2(i,0.5);
                alpha = 1.0;
                g_color = verts[i].color;
                EmitVertex();
            }
            EndPrimitive();
        }
    }
    // Draw Rectange
    for (int i = 0; i < 4; ++i) {
        gl_Position = coords[i];
        mTexCoord = texCoords[i];
        g_color = colors[i];
        alpha = alphas[i];
        EmitVertex();
    }
    EndPrimitive();


}