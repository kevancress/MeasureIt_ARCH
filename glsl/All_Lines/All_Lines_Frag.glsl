in vec2 mTexCoord;
in vec4 gl_FragCoord;
in vec4 g_color;

in vec4 f_dash_sizes;
in vec4 f_gap_sizes;
flat in int f_dashed;

uniform bool depthPass;

out vec4 fragColor;

float get_pattern_size(){
    float pattern_size = 0.0;
    for (int i = 0; i < 4; ++i) {
        pattern_size += f_dash_sizes[i];
        pattern_size += f_gap_sizes[i];
    }
    return pattern_size;
}

void main() {
    vec4 finalColor = g_color;
    vec4 aaColor = vec4(finalColor[0],finalColor[1],finalColor[2],finalColor[3]);
    vec4 mixColor = vec4(finalColor[0],finalColor[1],finalColor[2],0);

    vec2 center = vec2(0,0.5);
    float distFromEdge = 1-abs((mTexCoord.y*2)-1);

    float delta = fwidth(distFromEdge);
    float threshold = 1.5 * delta;
    float aa = clamp((distFromEdge/threshold)+0.4,0,1);
    aa = smoothstep(0,1,aa);

    aaColor = mix(mixColor,aaColor,aa);

    if (depthPass) {
        if (aa<1){
            discard;
        }
    }

    if(f_dashed == 1){
        float pattern_size = get_pattern_size();
        float d1 = f_dash_sizes[0];
        float d2 = f_dash_sizes[1];
        float d3 = f_dash_sizes[2];
        float d4 = f_dash_sizes[3];

        float g1 = f_gap_sizes[0];
        float g2 = f_gap_sizes[1];
        float g3 = f_gap_sizes[2];
        float g4 = f_gap_sizes[3];

        float arc_length = fract(mTexCoord.x/pattern_size)*pattern_size;
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
    

    fragColor = blender_srgb_to_framebuffer_space(aaColor);
    //fragColor = vec4(fract(mTexCoord),aaColor[2],1.0);
}