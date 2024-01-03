
//in vec4 color
//uniform vec4 overlay_color

void main() {
    vec4 finalColor = color;

    if (overlay_color.a != 0.0){
        finalColor = overlay_color;
    }
    float aa = finalColor[3];

    vec4 outColor = vec4(finalColor[0],finalColor[1],finalColor[2],aa);
    fragColor = outColor;
}