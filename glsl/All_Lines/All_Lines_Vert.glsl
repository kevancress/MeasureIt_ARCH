in vec3 pos;
in float weight;
in vec4 color;
in int rounded;

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