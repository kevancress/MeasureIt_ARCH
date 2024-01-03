
//in vec4 color
//in vec2 v_uv
//uniform vec4 overlay_color
// uniform bool depth_pass

void main() {
    vec4 finalColor = color;

    if (overlay_color.a != 0.0){
        finalColor = overlay_color;
    }
    float aa = finalColor[3];

    //aa = 1.0-(smoothstep(0.9a5,1.0,v_uv.y) + smoothstep(0.05,0.0,v_uv.y));
    float dist = (v_uv.y - 0.5)*2.0;

    aa = (1.0-smoothstep(0.6,1.0,abs(dist))) / fwidth(dist);

    if (depth_pass && aa < 1.0){
        discard;
    }

    vec4 outColor = vec4(finalColor[0],finalColor[1     ],finalColor[2],aa);
    fragColor = outColor;
}