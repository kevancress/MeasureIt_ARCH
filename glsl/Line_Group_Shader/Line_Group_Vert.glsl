uniform mat4 ModelViewProjectionMatrix;
in vec3 pos;
in float weight;

out VS_OUT {
    float weightOut;
} vs_out;

void main() {
    gl_Position = vec4(pos, 1.0);
    vs_out.weightOut = weight;
}