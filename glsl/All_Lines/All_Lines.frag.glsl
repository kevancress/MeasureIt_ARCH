//#version 330

in vec2 mTexCoord;
in vec4 gl_FragCoord;
in vec4 g_color;

uniform bool depthPass;
uniform vec4 dash_sizes;
uniform vec4 gap_sizes;
uniform bool dashed;
uniform vec4 overlay_color;

out vec4 fragColor;

float get_pattern_size(){
    float pattern_size = 0.0;
    for (int i = 0; i < 4; ++i) {
        pattern_size += dash_sizes[i];
        pattern_size += gap_sizes[i];
    }
    return pattern_size;
}

void main() {
    vec4 finalColor = g_color;
    if (overlay_color != vec4(0,0,0,0)){
        finalColor = overlay_color;
    }
    vec4 aaColor = vec4(finalColor[0],finalColor[1],finalColor[2],finalColor[3]);
    vec4 mixColor = vec4(finalColor[0],finalColor[1],finalColor[2],0);

    vec2 center = vec2(0,0.5);
    float distFromEdge = 1-abs((mTexCoord.y*2)-1);

    float delta = fwidth(distFromEdge);
    float threshold = 1.0 * delta;
    float aa = clamp((distFromEdge/threshold),0.0,1.0);
    aa = smoothstep(0,1,aa);

    aaColor = mix(mixColor,aaColor,aa);

    if (depthPass) {
        if (aa<1){
            discard;
        }
    }

    if(dashed){
        float pattern_size = get_pattern_size();
        float d1 = dash_sizes[0];
        float d2 = dash_sizes[1];
        float d3 = dash_sizes[2];
        float d4 = dash_sizes[3];

        float g1 = gap_sizes[0];
        float g2 = gap_sizes[1];
        float g3 = gap_sizes[2];
        float g4 = gap_sizes[3];

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