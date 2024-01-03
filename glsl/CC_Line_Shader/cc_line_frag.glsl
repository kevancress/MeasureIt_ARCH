
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

    float dist = (uv.y - 0.5)*2.0;

    aa = (1.0-smoothstep(0.6,1.0,abs(dist))) / fwidth(dist);

    if (depth_pass && aa < 1.0){
        discard;
    }

    
    if(dashed){
        float pattern_size = 0.0;
        for (int i = 0; i < 4; ++i) {
            pattern_size += dash_sizes[i];
            pattern_size += gap_sizes[i];
        }

        float d2 = dash_sizes[1];
        float d3 = dash_sizes[2];
        float d1 = dash_sizes[0];
        float d4 = dash_sizes[3];

        float g1 = gap_sizes[0];
        float g2 = gap_sizes[1];
        float g3 = gap_sizes[2];
        float g4 = gap_sizes[3];

        float arc_length = fract(uv.x/pattern_size*72.0)*pattern_size;
        // Discard first gap
        float gap_start = d1/2;
        if (arc_length > gap_start && arc_length < gap_start+g1){
            discard;
        }
        // Discard second gap
        gap_start += g1+d2;
        if (arc_length > gap_start && arc_length < gap_start+g2){
            discard;
        }

        gap_start += g2+d3;
        if (arc_length > gap_start && arc_length < gap_start+g3){
            discard;
        }

        gap_start += g3+d4;
        if (arc_length > gap_start && arc_length < gap_start+g4){
            discard;
        }
    }

    vec4 outColor = vec4(finalColor[0],finalColor[1],finalColor[2],aa);
    fragColor = outColor;
}