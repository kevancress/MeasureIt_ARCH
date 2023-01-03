uniform mat4 ModelViewProjectionMatrix;

in vec3 pos;
in vec2 uv;

out vec2 uvInterp;

vec4 project = ModelViewProjectionMatrix * vec4(pos, 1.0);
vec4 vecOffset = vec4(0.0,0.0,-0.001,0.0);

void main() {
    uvInterp = uv;
    gl_Position = project + vecOffset;
}