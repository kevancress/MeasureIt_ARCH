# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8 compliant>

# ----------------------------------------------------------
#
# Author: Kevan Cress
#
# ----------------------------------------------------------




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
        in vec4 fColor;
        out vec4 fragColor;


        void main()
        {

            fragColor = color;

        }

    '''

    geometry_shader = '''
        layout(lines) in;
        layout(triangle_strip, max_vertices = 10) out;
        out vec4 fColor;

        uniform float renderSize;
        uniform vec4 color;
        uniform mat4 ModelViewProjectionMatrix;
        uniform float thickness;

        

        // scale thickness from meaningful user input to usable value
        float offset = thickness*(0.001);

        void main() {
            //get line endpoint screen positions as vec2
            vec2 p0 = vec2(gl_in[0].gl_Position[0], gl_in[0].gl_Position[1]);
            vec2 p1 = vec2(gl_in[1].gl_Position[0], gl_in[1].gl_Position[1]);

            //calculate line normal
            vec2 line = p1-p0;
            vec2 lineNrml = normalize(line);
            vec2 norm = normalize(vec2(-line[1],line[0]));
            
            // get offset factor from normal and user input thicknes
            vec4 normFac = vec4(offset*norm[0], offset*norm[1], 0.0, 0.0);

            vec4 tanFac = vec4(offset*lineNrml[0], offset*lineNrml[1],0.0,0.0);

            gl_Position = gl_in[0].gl_Position-tanFac;
            EmitVertex();

            gl_Position = gl_in[0].gl_Position-normFac;
            EmitVertex();
            
            gl_Position = gl_in[1].gl_Position+tanFac;
            EmitVertex();

            gl_Position = gl_in[1].gl_Position-normFac;
            EmitVertex();

            gl_Position = gl_in[0].gl_Position-normFac;
            EmitVertex();

            gl_Position = gl_in[1].gl_Position+tanFac;
            EmitVertex();

            gl_Position = gl_in[1].gl_Position+normFac;
            EmitVertex();

            gl_Position = gl_in[0].gl_Position+normFac;
            EmitVertex();

            gl_Position = gl_in[0].gl_Position-tanFac;
            EmitVertex();

            gl_Position = gl_in[1].gl_Position+tanFac;
            EmitVertex();
            
            EndPrimitive();
        }  
    '''

class Base_Shader_3D ():

    vertex_shader = '''

        uniform mat4 ModelViewProjectionMatrix;
        //uniform bool isOtho;
        in vec3 pos;
        

        vec4 offset = vec4(0.0, 0.0, -0.001, 0.0);

        //if ( isOrtho ) {
        //    offset = vec4(0.0, 0.0, -0.0001, 0.0);
        //}


        void main()
        {
            vec3 newPos = pos;
            vec4 project = ModelViewProjectionMatrix * vec4(newPos, 1.0);
            gl_Position = project + offset;
        }

        '''
    geometry_shader = '''
        layout(lines) in;
        layout(line_strip, max_vertices = 4) out;

        uniform vec4 color;
        uniform mat4 ModelViewProjectionMatrix;
        uniform float thickness;

        void main()
        {
            gl_Position = gl_in[0].gl_Position;
            EmitVertex();

            gl_Position = gl_in[1].gl_Position;
            EmitVertex();

            EndPrimitive();
        }
        '''

    fragment_shader = '''
        uniform vec4 finalColor;
        out vec4 fragColor;
        in vec4 fColor;

        void main()
        {
            //vec4 depthCol = vec4(vec3(gl_FragCoord.z), 1.0);
            fragColor = finalColor;
        }
    '''

class Dashed_Shader_3D ():

    vertex_shader = '''
    uniform mat4 ModelViewProjectionMatrix;

    in vec3 pos;
    in float arcLength;    
    
    out float v_ArcLength;

    void main()
    {
        v_ArcLength = arcLength;
        gl_Position = ModelViewProjectionMatrix * vec4(pos, 1.0f);
    }
    '''

    fragment_shader = '''
        uniform float u_Scale;
        uniform vec4 finalColor;
        
        in float v_ArcLength;
        
        void main()
        {
            if (step(sin(v_ArcLength * u_Scale), 0.5) == 1) discard;
            gl_FragColor = finalColor;
        }
    '''

class Silhouette_Shader_3D ():

    vertex_shader = '''

        uniform mat4 ModelViewProjectionMatrix;
        //uniform bool isOtho;

        in vec3 pos;

        vec4 offset = vec4(0.0, 0.0, 0.003, 0.0);

        //if isOrtho {
        //    offset = vec4(0.0, 0.0, 0.00001, 0.0);
        //}


        void main()
        {
            vec3 newPos = pos;
            vec4 project = ModelViewProjectionMatrix * vec4(newPos, 1.0);
            gl_Position = project + offset;
        }

        '''