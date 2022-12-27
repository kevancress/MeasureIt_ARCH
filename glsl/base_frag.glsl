uniform vec4 finalColor;
out vec4 fragColor;
uniform bool depthPass;

void main() {
    float aa = finalColor[3];

    if(depthPass){
        aa = 1.0;
    }

    vec4 outColor = vec4(finalColor[0],finalColor[1],finalColor[2],aa);
    fragColor = blender_srgb_to_framebuffer_space(outColor);

}