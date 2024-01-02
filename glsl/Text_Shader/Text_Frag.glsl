//uniform sampler2D image;

//in vec2 uvInterp;
//out vec4 fragColor;

void main() {
    vec4 color = texture(image, uvInterp);

    if(color[3]<0.5){
        discard;
    }

    fragColor = color;
}