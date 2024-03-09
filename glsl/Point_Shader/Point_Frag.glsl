void main() {
    float aa = finalColor[3];

    vec2 dist_center = uv;
    float dist = length(dist_center);

   
    aa = clamp((1.0-smoothstep(0.6,1.0,abs(dist))) / fwidth(dist),0.0,1.0);
    if (aa < 1.0){
        discard;
    }
    vec4 outColor = vec4(finalColor[0],finalColor[1],finalColor[2],finalColor[3]*aa);
    fragColor = outColor;
}