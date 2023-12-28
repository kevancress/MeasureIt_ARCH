void main() {
    vec4 finalColor = color;
    float aa = finalColor[3];

    vec4 outColor = vec4(finalColor[0],finalColor[1],finalColor[2],aa);
    fragColor = outColor;
}