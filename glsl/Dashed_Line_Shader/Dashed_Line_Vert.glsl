uniform mat4 ModelViewProjectionMatrix;
uniform mat4 objectMatrix;
uniform float offset;

in vec3 pos;
out vec3 v_arcpos;

vec4 worldPos = objectMatrix * vec4(pos, 1.0);
vec4 project = ModelViewProjectionMatrix * worldPos;
vec4 vecOffset = vec4(0.0,0.0,offset,0.0);

void main() {
    gl_Position = project + vecOffset;
    v_arcpos = pos;
}