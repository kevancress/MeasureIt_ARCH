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
# Collection of Shaders for the Various Draw Functions.
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

class Base_Shader_3D ():

    vertex_shader = '''

        #ifdef USE_WORLD_CLIP_PLANES
        uniform mat4 ModelMatrix;
        #endif

        uniform mat4 ModelViewProjectionMatrix;
        uniform float offset;
        in vec3 pos;
        
        vec4 project = ModelViewProjectionMatrix * vec4(pos, 1.0);
        vec4 vecOffset = vec4(0.0,0.0,offset,0.0);

        void main()
        {
           gl_Position = project + vecOffset;

        #ifdef USE_WORLD_CLIP_PLANES
           world_clip_planes_calc_clip_distance((ModelMatrix * vec4(pos, 1.0)).xyz);
        #endif
        }

        '''

    fragment_shader = '''
        uniform vec4 finalColor;
        out vec4 fragColor;

        void main()
        {
            fragColor = finalColor;
        }
    '''

class Line_Shader_3D ():
    geometry_shader = '''
        layout(lines) in;
        layout(triangle_strip, max_vertices = 10) out;

        uniform mat4 ModelViewProjectionMatrix;
        uniform vec2 Viewport;
        uniform float thickness;

        out vec2 mTexCoord;

        float aspect = Viewport.x/Viewport.y;

        void main() {
            //calculate line normal

            vec4 p1 =  gl_in[0].gl_Position;
            vec4 p2 =  gl_in[1].gl_Position;
            
            vec2 ssp1 = vec2(p1.xy / p1.w);
            vec2 ssp2 = vec2(p2.xy / p2.w);

            float width = 0.00118 * thickness * aspect ;

            vec2 dir = normalize(ssp2 - ssp1);
            vec2 normal = vec2(-dir[1], dir[0]);

            // get offset factor from normal and user input thicknes
            vec2 offset = vec2(normal * width);
            offset.x /= aspect;
            

            vec4 coords[4];
            vec2 texCoords[4];
            coords[0] = vec4((ssp1 + offset)*p1.w,p1.z,p1.w);
            texCoords[0] = vec2(0,1);

            coords[1] = vec4((ssp1 - offset)*p1.w,p1.z,p1.w);
            texCoords[1] = vec2(0,0);

            coords[2] = vec4((ssp2 + offset)*p2.w,p2.z,p2.w);
            texCoords[2] = vec2(0,1);

            coords[3] = vec4((ssp2 - offset)*p2.w,p2.z,p2.w);
            texCoords[3] = vec2(0,0);

            for (int i = 0; i < 4; ++i) {
                mTexCoord = texCoords[i];
                gl_Position = coords[i];
                EmitVertex();
            }
            EndPrimitive();
        }  
    '''

    fragment_shader = '''
        in vec2 mTexCoord;
        uniform vec4 finalColor;
        out vec4 fragColor;

        void main()
        {
            vec4 aaColor = finalColor;

            vec2 center = vec2(0,0.5);
            float dist = length(mTexCoord - center);
            float distFromEdge = 1-(dist*2);

            float delta = fwidth(distFromEdge);
            float threshold = 2*delta;
            float aa = clamp((distFromEdge/threshold)+0.5,0,1);
            aa = aa -clamp(0.5*fwidth(aa),0,1);

            aaColor[3] = mix(0,1.0,aa);
            if (finalColor[3]<0.75){
                aaColor[3] *=0.25;
            }

            fragColor = aaColor;
        }
    '''

class Dashed_Shader_3D ():

    vertex_shader = '''
        uniform mat4 ModelViewProjectionMatrix;

        in vec3 pos;
        in float arcLength;    
        
        out float v_ArcLength;

        vec4 project = ModelViewProjectionMatrix * vec4(pos, 1.0f);
        vec4 offset = vec4(0,0,0,0);

        void main()
        {
            v_ArcLength = arcLength;
            gl_Position = project + offset;
        }
    '''
    geometry_shader = '''
        layout(lines) in;
        layout(triangle_strip, max_vertices = 10) out;
        in float v_ArcLength[];
        out float g_ArcLength;

        uniform vec2 Viewport;
        uniform float thickness;

        float aspect = Viewport.x/Viewport.y;
        
        void main() {
            //calculate line normal

            vec4 p1 =  gl_in[0].gl_Position;
            vec4 p2 =  gl_in[1].gl_Position;

            vec2 ssp1 = vec2(p1.xy / p1.w);
            vec2 ssp2 = vec2(p2.xy / p2.w);

            float width = 0.00118 * thickness;

            vec2 dir = normalize(ssp2 - ssp1);
            vec2 normal = vec2(-dir[1], dir[0]);
            
            // get offset factor from normal and user input thicknes
            vec2 offset = vec2(normal * width);
            offset.x /= aspect;

            vec4 coords[4];
            coords[0] = vec4((ssp1 + offset),(p1.z/p1.w),1.0);
            coords[1] = vec4((ssp1 - offset),(p1.z/p1.w),1.0);
            coords[2] = vec4((ssp2 + offset),(p2.z/p2.w),1.0);
            coords[3] = vec4((ssp2 - offset),(p2.z/p2.w),1.0);

            float arcLengths[4];
            arcLengths[0] = v_ArcLength[0];
            arcLengths[1] = v_ArcLength[0];
            arcLengths[2] = v_ArcLength[1];
            arcLengths[3] = v_ArcLength[1];

            for (int i = 0; i < 4; ++i) {
                gl_Position = coords[i];
                g_ArcLength = arcLengths[i];
                EmitVertex();
            }
            EndPrimitive();
        }  
    '''

    fragment_shader = '''
        uniform float u_Scale;
        uniform vec4 finalColor;
        
        in float g_ArcLength;
        out vec4 fragColor;

        void main()
        {
            if (step(sin(g_ArcLength * u_Scale), 0.5) == 1) discard;
            fragColor = finalColor;
        }
    '''

class Point_Shader_3D ():

   
    vertex_shader = '''

        uniform mat4 ModelViewProjectionMatrix;
        uniform float offset;
        in vec3 pos;
        
        vec4 project = ModelViewProjectionMatrix * vec4(pos, 1.0);
        vec4 vecOffset = vec4(0.0,0.0,offset,0.0);

        void main()
        {
            gl_Position = project + vecOffset;
        }

        '''

    geometry_shader = '''
        layout(points) in;
        layout(triangle_strip, max_vertices = 50) out;
        out vec2 mTexCoord;

        uniform mat4 ModelViewProjectionMatrix;
        uniform vec2 Viewport;
        uniform float thickness;

        float aspect = Viewport.x/Viewport.y;
        float radius = 0.00117 * thickness * aspect;

        vec4 p1 =  gl_in[0].gl_Position;
        vec2 ssp1 = vec2(p1.xy / p1.w);

        int segments = int(thickness) + 5;

        const float PI = 3.1415926;

        void main() {

            gl_Position = gl_in[0].gl_Position;
            EmitVertex();
            
            if (segments > 24){
                segments = 24;
            }

            for (int i = 0; i <= segments; i++) {
                // Angle between each side in radians
                float ang = PI * 2.0 / segments * i;

                // Offset from center of point
                vec2 offset = vec2(cos(ang)*radius, -sin(ang)*radius);
                offset.x /= aspect;
                mTexCoord = normalize(offset - ssp1);
                gl_Position = vec4((ssp1 + offset)*p1.w,p1.z,p1.w);
                EmitVertex();

                gl_Position = gl_in[0].gl_Position;
                mTexCoord = vec2(0,0);
                EmitVertex();

            }

            EndPrimitive();
        }  
    '''

    fragment_shader = '''
        in vec2 mTexCoord;
        uniform vec4 finalColor;
        out vec4 fragColor;

        void main()
        {
            vec4 aaColor = finalColor;

            vec2 center = vec2(0,0);
            float dist = length(mTexCoord - center);
            float distFromEdge = 1-(dist);

            float delta = fwidth(distFromEdge);
            float threshold = 2*delta;
            float aa = clamp((distFromEdge/threshold)+0.5,0,1);
            aa = aa -clamp(0.5*fwidth(aa),0,1);

            aaColor[3] = mix(0,1.0,aa);
            if (finalColor[3]<0.75){
                aaColor[3] *=0.25;
            }

            fragColor = aaColor;
        }
    '''

class Text_Shader():
    vertex_shader = '''
    uniform mat4 ModelViewProjectionMatrix;

    in vec3 pos;
    in vec2 uv;

    out vec2 uvInterp;

    vec4 project = ModelViewProjectionMatrix * vec4(pos, 1.0);
    vec4 vecOffset = vec4(0.0,0.0,-0.001,0.0);

    void main()
    {
        uvInterp = uv;
        gl_Position = project + vecOffset;
    }
    '''

    fragment_shader = '''
        uniform sampler2D image;

        in vec2 uvInterp;
        out vec4 fragColor;

        void main()
        {
            fragColor = texture(image, uvInterp);
        }
    '''

class DepthOnlyFrag():
    fragment_shader = ''' 
        out vec4 fragColor;

        void main()
        {
            fragColor = vec4(gl_FragCoord.z,gl_FragCoord.z,gl_FragCoord.z,1.0);
        }
    '''

class Pass_Through_Geo():

    geometry_shader = '''
        layout(lines) in;
        layout(line_strip, max_vertices = 4) out;
        
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