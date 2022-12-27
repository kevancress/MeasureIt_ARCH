uniform mat4 ModelViewProjectionMatrix;

in vec3 pos;
in float weight;
in vec4 color;
in float offset;
in int rounded;
in mat4 objectMatrix;

out float v_weight;
out float v_offset;
out vec4 v_color;
out int v_rounded;
out mat4 v_objectMatrix;

vec4 project = ModelViewProjectionMatrix * vec4(pos, 1.0);

void main() {
    gl_Position = vec4(pos, 1.0);
    v_weight = weight;
    v_color = color;
    v_offset = offset;
    v_rounded = int(rounded);
    v_objectMatrix = objectMatrix;
}