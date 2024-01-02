//uniform mat4 viewProjectionMatrix;
//uniform float offset;
//uniform float pointSize
//in vec3 pos;

void main() {
    vec4 project = viewProjectionMatrix * vec4(pos, 1.0);
    vec4 vecOffset = vec4(0.0,0.0,offset,0.0);
    gl_Position = project + vecOffset;
    gl_PointSize = pointSize;
}