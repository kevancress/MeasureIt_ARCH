//uniform mat4 viewProjectionMatrix;
//uniform float offset;
//uniform float pointSize
// uniform float view_scale
//in vec3 pos;
// in vec2 exp_dir

// out vec2 uv

void main() {

    float paper_space_exp = pointSize/72/39.37 * view_scale; // weight from p to paper space m for world space expansion (devided by two since we expand from center)

    vec3 perp_x = normalize(cross(vec3(1,0,0),view_dir.xyz));
    vec3 perp_y = normalize(cross(perp_x,view_dir.xyz));
    vec3 exp_pos = pos.xyz + perp_x*exp_dir.x*paper_space_exp + perp_y*exp_dir.y * paper_space_exp;
    vec4 project = viewProjectionMatrix * vec4(exp_pos, 1.0);

    gl_Position = vec4(project.x,project.y,project.z + offset, project.w);
    uv = exp_dir;
}