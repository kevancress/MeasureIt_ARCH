void main() {
    float aa = finalColor[3];

    vec2 dist_center = gl_PointCoord - vec2(0.5);
    float dist = length(dist_center);
    if (dist > 0.5){
        discard;
    }

    aa = smoothstep(0.5,0.51,1.0-dist);
    vec4 outColor = vec4(finalColor[0],finalColor[1],finalColor[2],aa);
    fragColor = outColor;
}