
layout(lines) in;
layout(triangle_strip, max_vertices = 10) out;
in vec3 v_arcpos[];
out float g_ArcLength;
out float alpha;

uniform mat4 ModelViewProjectionMatrix;
uniform vec2 Viewport;
uniform vec2 Render;
uniform float resolution;
uniform float thickness;
uniform bool screenSpaceDash;
out vec2 mTexCoord;

float aspect = Viewport.x/Viewport.y;

vec2 pxVec = vec2(1.0/Viewport.x,1.0/Viewport.y);
float minLength =  1.0* length(pxVec);

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
// calculate line normal

vec4 p1 =  gl_in[0].gl_Position;
vec4 p2 =  gl_in[1].gl_Position;

vec2 ssp1 = vec2(p1.xy / p1.w);
vec2 ssp2 = vec2(p2.xy / p2.w);

float width = thickness;

vec2 dir = normalize(ssp2 - ssp1);
vec2 normal = vec2(-dir[1], dir[0]);

// get offset factor from normal and user input thicknes
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


float arcLengths[4];
arcLengths[0] = 0;
arcLengths[1] = 0;
float scale_fac = Render.x / Viewport.x;
if (screenSpaceDash){

    arcLengths[2] = length(ssp2-ssp1)*resolution*scale_fac;
    arcLengths[3] = length(ssp2-ssp1)*resolution*scale_fac;
} else {
    arcLengths[2] = length(v_arcpos[1]-v_arcpos[0])*resolution;
    arcLengths[3] = length(v_arcpos[1]-v_arcpos[0])*resolution;
}

for (int i = 0; i < 4; ++i) {
    mTexCoord = texCoords[i];
    gl_Position = coords[i];
    g_ArcLength = arcLengths[i];
    alpha = lineAlpha;
    EmitVertex();
}
EndPrimitive();
}