layout(lines) in;
layout(triangle_strip, max_vertices = 64) out;

in VS_OUT {
    float weightOut;
} gs_in[];

uniform mat4 ModelViewProjectionMatrix;
uniform mat4 objectMatrix;
uniform vec2 Viewport;
uniform float thickness;
uniform float extension;
uniform float zOffset;
uniform float weightInfluence;
uniform bool pointPass;

const float PI = 3.1415926;
out vec2 mTexCoord;
out float alpha;

float width = thickness;
float extAmount = extension * 0.01;
vec4 vecOffset = vec4(0.0,0.0,zOffset,0.0);
float radius = width;

vec2 pxVec = vec2(1.0/Viewport.x,1.0/Viewport.y);
float view_ratio = Viewport.x / Viewport.y;

float minLength = 1.0*length(pxVec);

vec2 get_ss_width_from_ws(){
    mat4 inv_proj_mat = inverse(ModelViewProjectionMatrix);
    vec4 p1ss = vec4(0.0,0.0,0.0,1.0);
    vec4 p2ss = vec4(1.0,0.0,0.0,1.0);
    vec4 p3ss = vec4(0.0,1.0,0.0,1.0);
    vec4 p1ws = inv_proj_mat * p1ss;
    vec4 p2ws = inv_proj_mat * p2ss;
    vec4 p3ws = inv_proj_mat * p3ss;
    p1ws.xyz *= p1ws.w;
    p2ws.xyz *= p2ws.w;
    p3ws.xyz *= p3ws.w;
    float ws_dist_x = length((p2ws.xyz)- (p1ws.xyz));
    float ws_dist_y = length((p3ws.xyz) - (p1ws.xyz));
    return vec2(1.0/ws_dist_x,1.0/ws_dist_y);
}

vec2 ws_ratio = get_ss_width_from_ws();

vec2 get_line_width(vec2 normal, float width) {
    vec2 offsetvec = vec2(normal * width);
    offsetvec *= pxVec;
    offsetvec *= ws_ratio.x;
    offsetvec *= view_ratio * 8.125;

    if (length(offsetvec) < minLength){
        offsetvec = normalize(offsetvec);
        offsetvec *= minLength;
    }
    return(offsetvec);
}

float get_line_alpha(vec2 normal, float width) {
    vec2 offsetvec = vec2(normal * width);
    offsetvec *= pxVec;
    offsetvec *= ws_ratio.x;
    offsetvec *= view_ratio * 8.125;

    float alpha = 1.0;
    if (length(offsetvec) < minLength){
        alpha *= (length(offsetvec)/minLength);
    }
    return alpha;
}


void main() {
    // Calculate world space line normal and extension
    vec4 p1 =  gl_in[0].gl_Position;
    vec4 p2 =  gl_in[1].gl_Position;

    vec4 dir3d = vec4(normalize(p2.xyz-p1.xyz),0);

    vec4 p1ExtLocal = vec4(p1 - dir3d*extAmount);
    vec4 p2ExtLocal = vec4(p2 + dir3d*extAmount);

    // Project to Clip space Using Object and veiw matrix
    vec4 p1worldPos = objectMatrix * p1ExtLocal;
    vec4 p1project = ModelViewProjectionMatrix * p1worldPos;

    vec4 p2worldPos = objectMatrix * p2ExtLocal;
    vec4 p2project = ModelViewProjectionMatrix * p2worldPos;

    // Add Z offset
    vec4 p1Ext = p1project + vecOffset;
    vec4 p2Ext = p2project + vecOffset;

    // Get Screen Space points
    vec2 ssp1 = vec2(p1Ext.xy / p1Ext.w);
    vec2 ssp2 = vec2(p2Ext.xy / p2Ext.w);

    // Get Width per point
    float width1 = mix(width, gs_in[0].weightOut * width, weightInfluence);
    radius = width1;

    float width2 = mix(width, gs_in[1].weightOut * width, weightInfluence);

    // Screen Space direction and normal
    vec2 dir = normalize(ssp2 - ssp1);
    vec2 normal = vec2(-dir[1], dir[0]);
    normal = normalize(normal);

    // Screen Space line width offset
    vec2 lineOffset1 = get_line_width(normal,width1);
    float alpha1 = get_line_alpha(normal,width1);

    vec2 lineOffset2 = get_line_width(normal, width2);
    float alpha2 = get_line_alpha(normal,width2);

    // Generate the rectangle Coords
    vec4 coords[4];
    vec2 texCoords[4];
    float alphas[4];

    coords[0] = vec4((ssp1 + lineOffset1)*p1Ext.w,p1Ext.z,p1Ext.w);
    texCoords[0] = vec2(0,1);
    alphas[0] = alpha1;

    coords[1] = vec4((ssp1 - lineOffset1)*p1Ext.w,p1Ext.z,p1Ext.w);
    texCoords[1] = vec2(0,0);
    alphas[1] = alpha1;

    coords[2] = vec4((ssp2 + lineOffset2)*p2Ext.w,p2Ext.z,p2Ext.w);
    texCoords[2] = vec2(0,1);
    alphas[2] = alpha2;

    coords[3] = vec4((ssp2 - lineOffset2)*p2Ext.w,p2Ext.z,p2Ext.w);
    texCoords[3] = vec2(0,0);
    alphas[3] = alpha2;

    // Draw Point pass
    // Get Center Point in Screen Space
    radius = width * get_ss_width_from_ws().x * view_ratio * 8.125;
    if (pointPass){
        vec4 worldPos = objectMatrix * p1;
        vec4 project = ModelViewProjectionMatrix * worldPos;

        vec4 pointCenter = project + vecOffset;
        vec2 sspC = vec2(pointCenter.xy / pointCenter.w);

        // Get number of segments in the circle
        int segments = int(floor(thickness)) + 5;
        segments = clamp(segments,0,28);

        // Generate Circle
        gl_Position = pointCenter;
        mTexCoord = vec2(0.0,0.5);
        EmitVertex();

        for (int i = 0; i <= segments; i++) {
            // Angle between each side in radians
            float ang = PI * 2.0 / float(segments) * float(i);

            // Offset from center of point
            vec2 circleOffset = vec2(cos(ang)*radius, -sin(ang)*radius);
            circleOffset.x /= Viewport.x;
            circleOffset.y /= Viewport.y;
            mTexCoord = vec2(0.0,1.0);
            gl_Position = vec4((sspC + circleOffset)*pointCenter.w, pointCenter.z, pointCenter.w);
            alpha = alpha1;
            EmitVertex();

            gl_Position = pointCenter;
            mTexCoord = vec2(0,0.5);
            EmitVertex();
        }

        EndPrimitive();

    }

    // Draw Rectange
    for (int i = 0; i < 4; ++i) {
        mTexCoord = texCoords[i];
        gl_Position = coords[i];
        alpha = alphas[i];
        EmitVertex();
    }
    EndPrimitive();
}