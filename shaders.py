class Base_Shader_2D ():
    vertex_shader = '''
        uniform mat4 ModelViewProjectionMatrix;
        in vec2 pos;
        void main()
        {
            gl_Position = ModelViewProjectionMatrix * vec4(pos, 0.0, 1.0);
        }
    
    '''

    fragment_shader = '''

        uniform vec4 color;
        out vec4 fragColor;

        void main()
        {
            fragColor = color;
        }

    '''

    geometry_shader = '''
        layout(lines) in;
        layout(triangle_strip, max_vertices = 4) out;

        uniform mat4 ModelViewProjectionMatrix;
        uniform float thickness;

        void main() {    
            vec2 p0 = vec2(gl_in[0].gl_Position[0], gl_in[0].gl_Position[1]);
            vec2 p1 = vec2(gl_in[1].gl_Position[0], gl_in[1].gl_Position[1]);
            vec2 line = p1-p0;
            vec2 norm = normalize(vec2(-line[1],line[0]));
            
            vec4 fac = vec4(thickness*norm[0], thickness*norm[1], 0.0, 0.0);
            gl_Position = gl_in[0].gl_Position+fac;
            EmitVertex();

            gl_Position = gl_in[1].gl_Position+fac;
            EmitVertex();

            gl_Position = gl_in[0].gl_Position-fac;
            EmitVertex();

            gl_Position = gl_in[1].gl_Position-fac;
            EmitVertex();
            
            EndPrimitive();
        }  
    '''
