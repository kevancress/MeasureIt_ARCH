uniform mat4 ModelViewProjectionMatrix;
uniform float offset;
in vec3 pos;
vec4 project = ModelViewProjectionMatrix * vec4(pos, 1.0);
vec4 vecOffset = vec4(0.0,0.0,offset,0.0);

void main() {
    gl_Position = project + vecOffset;
}