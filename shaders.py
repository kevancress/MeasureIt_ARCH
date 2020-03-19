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

            float width = 0.00118 * thickness * aspect;

            vec2 dir = normalize(ssp2 - ssp1);
            vec2 normal = vec2(-dir[1], dir[0]);

            // get offset factor from normal and user input thickness
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
            aa = smoothstep(0,1,aa);

            aaColor[3] = mix(0,finalColor[3],aa);

            fragColor = aaColor;

            fragColor = aaColor;
        }
    '''

class Line_Group_Shader_3D ():
    vertex_shader = '''

        uniform mat4 ModelViewProjectionMatrix;
        in vec3 pos;


        void main()
        {
           gl_Position = vec4(pos, 1.0);
        }

        '''


    geometry_shader = '''
        layout(lines) in;
        layout(triangle_strip, max_vertices = 60) out;

        uniform mat4 ModelViewProjectionMatrix;
        uniform mat4 objectMatrix;
        uniform vec2 Viewport;
        uniform float thickness;
        uniform float extension;
        uniform float offset;

        out vec2 mTexCoord;
        float aspect = Viewport.x/Viewport.y;

        void main() {
            //calculate line normal and extension

            vec4 p1 =  gl_in[0].gl_Position;
            vec4 p2 =  gl_in[1].gl_Position;

            vec4 dir3d = normalize(p2-p1);

            vec4 p1Ext = vec4(p1-dir3d*extension*0.01);
            vec4 p2Ext = vec4(p2+dir3d*extension*0.01);

            
            vec4 p1worldPos = objectMatrix * p1Ext;
            vec4 p1project = ModelViewProjectionMatrix * p1worldPos;

            vec4 p2worldPos = objectMatrix * p2Ext;
            vec4 p2project = ModelViewProjectionMatrix * p2worldPos;

            vec4 vecOffset = vec4(0.0,0.0,offset,0.0);

            p1Ext = p1project + vecOffset;
            p2Ext = p2project + vecOffset;
            
            vec2 ssp1 = vec2(p1Ext.xy / p1Ext.w);
            vec2 ssp2 = vec2(p2Ext.xy / p2Ext.w);

            float width = 0.00118 * thickness * aspect;

            vec2 dir = normalize(ssp2 - ssp1);
            vec2 normal = vec2(-dir[1], dir[0]);

            // get offset factor from normal and user input thickness
            vec2 offset = vec2(normal * width);
            offset.x /= aspect;
            
            // generate rect
            vec4 coords[4];
            vec2 texCoords[4];

            coords[0] = vec4((ssp1 + offset)*p1Ext.w,p1Ext.z,p1Ext.w);
            texCoords[0] = vec2(0,1);

            coords[1] = vec4((ssp1 - offset)*p1Ext.w,p1Ext.z,p1Ext.w);
            texCoords[1] = vec2(0,0);

            coords[2] = vec4((ssp2 + offset)*p2Ext.w,p2Ext.z,p2Ext.w);
            texCoords[2] = vec2(0,1);

            coords[3] = vec4((ssp2 - offset)*p2Ext.w,p2Ext.z,p2Ext.w);
            texCoords[3] = vec2(0,0);

            for (int i = 0; i < 4; ++i) {
                mTexCoord = texCoords[i];
                gl_Position = coords[i];
                EmitVertex();
            }
            EndPrimitive();

            //Draw Point pass
            p1 =  gl_in[0].gl_Position;
            vec4 worldPos = objectMatrix * p1;
            vec4 project = ModelViewProjectionMatrix * worldPos;

            p1 = project + vecOffset;
            ssp1 = vec2(p1.xy / p1.w);



            float radius = 0.00117 * thickness * aspect;
            int segments = int(thickness) + 5;

            const float PI = 3.1415926;
            
            gl_Position = p1;
            mTexCoord = vec2(0,0.5);
            EmitVertex();
            segments = clamp(segments,0,24);

            for (int i = 0; i <= segments; i++) {
                // Angle between each side in radians
                float ang = PI * 2.0 / segments * i;

                // Offset from center of point
                offset = vec2(cos(ang)*radius, -sin(ang)*radius);
                offset.x /= aspect;
                mTexCoord = vec2(0,1);
                gl_Position = vec4((ssp1 + offset)*p1.w,p1.z,p1.w);
                EmitVertex();

                gl_Position = p1;
                mTexCoord = vec2(0,0.5);
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
            aa = smoothstep(0,1,aa);

            aaColor[3] = mix(0,finalColor[3],aa);

            fragColor = aaColor;
        }
    '''

class Dashed_Shader_3D ():

    vertex_shader = '''
        uniform mat4 ModelViewProjectionMatrix;
        uniform mat4 objectMatrix;
        uniform float offset;

        in vec3 pos;
        out vec3 v_arcpos;

        vec4 worldPos = objectMatrix * vec4(pos, 1.0);
        vec4 project = ModelViewProjectionMatrix * worldPos;
        vec4 vecOffset = vec4(0.0,0.0,offset,0.0);

        void main()
        {
            gl_Position = project + vecOffset;
            v_arcpos = pos;
        }
    '''
    geometry_shader = '''
        layout(lines) in;
        layout(triangle_strip, max_vertices = 10) out;
        in vec3 v_arcpos[];
        out float g_ArcLength;

        uniform mat4 ModelViewProjectionMatrix;
        uniform vec2 Viewport;
        uniform float thickness;
        uniform bool screenSpaceDash;
        out vec2 mTexCoord;

        float aspect = Viewport.x/Viewport.y;
        
        void main() {
            //calculate line normal

            vec4 p1 =  gl_in[0].gl_Position;
            vec4 p2 =  gl_in[1].gl_Position;

            vec2 ssp1 = vec2(p1.xy / p1.w);
            vec2 ssp2 = vec2(p2.xy / p2.w);

            float width = 0.00118 * thickness * aspect;

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

            
            float arcLengths[4];
            arcLengths[0] = 0;
            arcLengths[1] = 0;
            
            if (screenSpaceDash){
                arcLengths[2] = length(ssp2-ssp1) * 20;
                arcLengths[3] = length(ssp2-ssp1) * 20;
            }
            else{
                arcLengths[2] = length(v_arcpos[1]-v_arcpos[0])*2;
                arcLengths[3] = length(v_arcpos[1]-v_arcpos[0])*2;
            }

            for (int i = 0; i < 4; ++i) {
                mTexCoord = texCoords[i];
                gl_Position = coords[i];
                g_ArcLength = arcLengths[i];
                EmitVertex();
            }
            EndPrimitive();
        }  
    '''

    fragment_shader = '''
        in vec2 mTexCoord;
        uniform float u_Scale;
        uniform vec4 finalColor;
        
        in float g_ArcLength;
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
            aa = smoothstep(0,1,aa);

            aaColor[3] = mix(0,finalColor[3],aa);

            fragColor = aaColor;

            if (step(sin(g_ArcLength * u_Scale), 0.5) == 1) discard;
            fragColor = aaColor;
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
            
            segments = clamp(segments,0,24);
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
            aa = smoothstep(0,1,aa);

            aaColor[3] = mix(0,finalColor[3],aa);

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