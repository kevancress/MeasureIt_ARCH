in vec3 pos;
in float weight;
in vec4 color;
in float offset;
in int rounded;
in mat4 objectMatrix;

out VERT_OUT {
    float weight;
    float offset;
    vec4 color;
    int rounded;
    mat4 objectMatrix;
} vert_out;

void main() {
    gl_Position = vec4(pos, 1.0);
    vert_out.weight = weight;
    vert_out.color = color;
    vert_out.offset = offset;
    vert_out.rounded = int(rounded);
    vert_out.objectMatrix = objectMatrix;
}