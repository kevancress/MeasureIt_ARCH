//uniform mat4 viewProjectionMatrix
//uniform float offset
// uniform mat4 objectMatrix
// uniform mat4 extMatrix
// uniform vec3 view_dir
// in vec4 col
// in vec3 dir
// in int thick_sign
// in float weight
// in vec2 v_uv

// out vec4 color
// out vec2 uv

void main() {

    vec3 perp = normalize(cross(dir.xyz,view_dir));
    vec3 exp_pos = pos + perp * thick_sign * weight/72.0;
    vec4 l_project = viewProjectionMatrix * objectMatrix *extMatrix* vec4(pos, 1.0);

    vec4 project = viewProjectionMatrix * objectMatrix *extMatrix* vec4(exp_pos, 1.0);
    gl_Position = vec4(project.x,project.y,l_project.z + offset,l_project.w);
    color = col;
    uv = v_uv;
}