uniform mat4 ModelViewProjectionMatrix;
out vec4 fragColor;

void main() {
    float depth = gl_FragCoord.z;
    fragColor = vec4(depth, depth, depth, 1.0);
}