in vec2 mTexCoord;
in vec4 gl_FragCoord;
in vec4 g_color;
in float alpha;

uniform bool depthPass;

out vec4 fragColor;

void main() {
    vec4 finalColor = g_color;
    vec4 aaColor = vec4(finalColor[0],finalColor[1],finalColor[2],alpha);
    vec4 mixColor = vec4(finalColor[0],finalColor[1],finalColor[2],0);

    vec2 center = vec2(0,0.5);
    float dist = length(mTexCoord - center);
    float distFromEdge = 1-(dist*2);

    float delta = fwidth(distFromEdge);
    float threshold = 1.5 * delta;
    float aa = clamp((distFromEdge/threshold)+0.5,0,1);
    aa = smoothstep(0,1,aa);

    aaColor = mix(mixColor,aaColor,aa);

    if (depthPass) {
        if (aa<1) {
            discard;
        }
    }

    fragColor = aaColor;
}