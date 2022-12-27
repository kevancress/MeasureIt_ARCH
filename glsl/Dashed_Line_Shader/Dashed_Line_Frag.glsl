
in vec2 mTexCoord;
uniform vec4 finalColor;
uniform float u_dashSize;
uniform float u_gapSize;
in float alpha;

in float g_ArcLength;
out vec4 fragColor;

void main() {
    vec4 aaColor = vec4(finalColor[0],finalColor[1],finalColor[2],alpha);
    vec4 mixColor = vec4(finalColor[0],finalColor[1],finalColor[2],0);

    vec2 center = vec2(0,0.5);
    float dist = length(mTexCoord - center);
    float distFromEdge = 1-(dist*2);

    float delta = fwidth(distFromEdge);
    float threshold = 1.5*delta;
    float aa = clamp((distFromEdge/threshold)+0.5,0,1);
    aa = smoothstep(0,1,aa);

    aaColor = mix(mixColor,aaColor,aa);


    if (fract(g_ArcLength / (u_dashSize + u_gapSize)) > u_dashSize/(u_dashSize + u_gapSize))discard;
    fragColor = blender_srgb_to_framebuffer_space(aaColor);
}