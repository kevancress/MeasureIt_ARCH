in vec3 pos;
in float weight;
in vec4 color;
in float offset;
in int rounded;
in mat4 objectMatrix;

in vec4 dash_sizes;
in vec4 gap_sizes;
flat in int dashed;

out VERT_OUT {
    float weight;
    float offset;
    vec4 color;
    int rounded;
    mat4 objectMatrix;
    vec4 dash_sizes;
    vec4 gap_sizes;
    int dashed;
} vert_out;

void main() {
    gl_Position = vec4(pos, 1.0);
    vert_out.weight = weight;
    vert_out.color = color;
    vert_out.offset = offset;
    vert_out.rounded = int(rounded);
    vert_out.objectMatrix = objectMatrix;
    vert_out.dash_sizes = dash_sizes;
    vert_out.gap_sizes = gap_sizes;
    vert_out.dashed = dashed;
}