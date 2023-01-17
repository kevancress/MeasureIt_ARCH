in vec3 pos;
in float weight;
in vec4 color;
in float offset;
in int rounded;
in mat4 objectMatrix;

in vec4 dash_sizes;
in vec4 gap_sizes;
in int dashed;

out VERT_OUT {
    float weight;
    vec4 color;
    int rounded;
} vert_out;

void main() {
    gl_Position = vec4(pos, 1.0);
    vert_out.weight = weight;
    vert_out.color = color;
    vert_out.rounded = int(rounded);
}