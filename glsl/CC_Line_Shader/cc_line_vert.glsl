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
// uniform float view_scale

// out vec4 color
// out vec2 uv

void main() {
    vec4 local_dir = objectMatrix *extMatrix* vec4(dir,0.0);
    vec4 local_pos = objectMatrix *extMatrix* vec4(pos, 1.0);
    //vec4 local_view = objectMatrix*vec4(view_dir,0.0);
    vec3 perp = normalize(cross(local_dir.xyz,view_dir.xyz));
    float paper_space_exp = weight/72/39.37 * view_scale; // weight from p to paper space m for world space expansion (devided by two since we expand from center)
    vec3 exp_pos = local_pos.xyz + perp * thick_sign * paper_space_exp; 
    vec4 l_project = viewProjectionMatrix * objectMatrix *extMatrix* vec4(pos, 1.0);

    vec4 project = viewProjectionMatrix * vec4(exp_pos, 1.0);
    gl_Position = vec4(project.x,project.y,l_project.z + offset, project.w);
    color = col;
    uv = v_uv;
}