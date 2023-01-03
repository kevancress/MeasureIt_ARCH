layout(points) in;
layout(triangle_strip, max_vertices = 50) out;
out vec2 mTexCoord;
out float alpha;

uniform mat4 ModelViewProjectionMatrix;
uniform vec2 Viewport;
uniform float thickness;

float aspect = Viewport.x/Viewport.y;

vec4 p1 =  gl_in[0].gl_Position;
vec2 ssp1 = vec2(p1.xy / p1.w);

int segments = int(floor(thickness)) + 5;

const float PI = 3.1415926;
float val = 0.8625;

vec2 pxVec = vec2(1.0/Viewport.x,1.0/Viewport.y);
float minLength =  length(pxVec);

vec2 get_line_width(vec2 normal, float width) {
    vec2 offsetvec = vec2(normal * width);
    offsetvec.x /= Viewport.x;
    offsetvec.y /= Viewport.y;

    if (length(offsetvec) < minLength){
        offsetvec = normalize(offsetvec);
        offsetvec *= minLength;
    }
    return(offsetvec);
}

float get_line_alpha(vec2 normal, float width) {
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
    gl_Position = gl_in[0].gl_Position;
    mTexCoord = vec2(0.0,0.5);

    float radius = length(get_line_width(vec2(val), thickness));
    float lineAlpha = get_line_alpha(vec2(val), thickness);
    EmitVertex();

    segments = clamp(segments,0,24);
    for (int i = 0; i <= segments; i++) {
        // Angle between each side in radians
        float ang = PI * 2.0 / float(segments) * float(i);

        // Offset from center of point
        vec2 offset = vec2(cos(ang)*radius, -sin(ang)*radius);
        offset.x /= aspect;
        mTexCoord = vec2(0,1);
        gl_Position = vec4((ssp1 + offset)*p1.w,p1.z,p1.w);
        alpha=lineAlpha;
        EmitVertex();

        gl_Position = gl_in[0].gl_Position;
        mTexCoord = vec2(0,0.5);
        alpha=lineAlpha;
        EmitVertex();

    }

    EndPrimitive();
}