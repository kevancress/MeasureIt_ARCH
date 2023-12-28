//uniform mat4 viewProjectionMatrix
//uniform float offset
// uniform mat4 objectMatrix
// in vec4 col

void main() {
    vec4 project = viewProjectionMatrix * objectMatrix * vec4(pos, 1.0);
    vec4 vecOffset = vec4(0.0,0.0,offset,0.0);
    gl_Position = project + vecOffset;
    color = col;
}