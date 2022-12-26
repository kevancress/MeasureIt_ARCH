layout(lines) in;
layout(triangle_strip, max_vertices = 10) out;

uniform mat4 ModelViewProjectionMatrix;
uniform vec2 Viewport;

in float v_weight[];
in vec4 v_color[];

out vec2 mTexCoord;
out float alpha;
out vec4 g_color;

float aspect = Viewport.x/Viewport.y;

vec2 pxVec = vec2(1.0/Viewport.x,1.0/Viewport.y);
float minLength =  length(pxVec);

vec2 get_line_width(vec2 normal, float width){
    vec2 offsetvec = vec2(normal * width);
    offsetvec.x /= Viewport.x;
    offsetvec.y /= Viewport.y;

    if (length(offsetvec) < minLength){
        offsetvec = normalize(offsetvec);
        offsetvec *= minLength;
    }
    return(offsetvec);
}

float get_line_alpha(vec2 normal, float width){
    vec2 offsetvec = vec2(normal * width);
    offsetvec.x /= Viewport.x;
    offsetvec.y /= Viewport.y;

    float alpha = 1.0;
    if (length(offsetvec) < minLength){
        alpha *= (length(offsetvec)/minLength);
    }
    return alpha;
}

void main() {
    //calculate line normal

    vec4 p1 =  gl_in[0].gl_Position;
    vec4 p2 =  gl_in[1].gl_Position;

    vec2 ssp1 = vec2(p1.xy / p1.w);
    vec2 ssp2 = vec2(p2.xy / p2.w);

    float width = v_weight[0];

    vec2 dir = normalize(ssp2 - ssp1);
    vec2 normal = vec2(-dir[1], dir[0]);
    normal = normalize(normal);

    // get offset factor from normal and user input thickness
    vec2 offset = get_line_width(normal,width);
    float lineAlpha = get_line_alpha(normal,width);

    vec4 coords[4];
    vec2 texCoords[4];

    coords[0] = vec4((ssp1 + offset)*p1.w,p1.z,p1.w);
    texCoords[0] = vec2(0,1);

    coords[1] = vec4((ssp1 - offset)*p1.w,p1.z,p1.w);
    texCoords[1] = vec2(0,0);

    coords[2] = vec4((ssp2 + offset)*p2.w,p2.z,p2.w);
    texCoords[2] = vec2(0,1);

    coords[3] = vec4((ssp2 - offset)*p2.w,p2.z,p2.w);
    texCoords[3] = vec2(0,0);

    for (int i = 0; i < 4; ++i) {
        mTexCoord = texCoords[i];
        gl_Position = coords[i];
        g_color = v_color[0];
        alpha = lineAlpha;
        EmitVertex();
    }
    EndPrimitive();
}