uniform mat4 ModelViewProjectionMatrix;

in vec3 pos;
in float weight;
in vec4 color;
in float offset;

out float v_weight;
out vec4 v_color;

vec4 project = ModelViewProjectionMatrix * vec4(pos, 1.0);
vec4 vecOffset = vec4(0.0,0.0,offset,0.0);

void main() {
    gl_Position = project + vecOffset;
    v_weight = weight;
    v_color = color;
}