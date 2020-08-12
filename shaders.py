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


class Base_Shader_3D_AA ():
    fragment_shader = '''
        in vec2 mTexCoord;
        in vec4 fcolor;
        in vec4 gl_FragCoord;
        uniform vec4 finalColor;
        uniform bool depthPass;
        out vec4 fragColor;

        void main()
        {
            vec4 aaColor = finalColor;
            vec4 mixColor = vec4(finalColor[0],finalColor[1],finalColor[2],0);

            vec2 center = vec2(0,0.5);
            float dist = length(mTexCoord - center);
            float distFromEdge = 1-(dist*2);

            float delta = fwidth(distFromEdge);
            float threshold = 1.5 * delta;
            float aa = clamp((distFromEdge/threshold)+0.5,0,1);
            aa = smoothstep(0,1,aa*aa);

            aaColor = mix(mixColor,finalColor,aa);

            if(depthPass){
                if (aa<1){
                    discard;
                }
            }
            
            fragColor = aaColor; 
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

            float width = 0.00118 * thickness * aspect * 1.333;

            vec2 dir = normalize(ssp2 - ssp1);
            vec2 normal = vec2(-dir[1], dir[0]);
            normal.x /= aspect;
            normal = normalize(normal);

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

class Line_Group_Shader_3D ():
    vertex_shader = '''

        uniform mat4 ModelViewProjectionMatrix;
        in vec3 pos;
        in float weight;

        out VS_OUT
        {
            float weightOut;
        } vs_out;

        void main()
        {
           gl_Position = vec4(pos, 1.0);
           vs_out.weightOut = weight*1.333*4;
        }

        '''


    geometry_shader = '''
        layout(lines) in;
        layout(triangle_strip, max_vertices = 64) out;

        in VS_OUT {
            float weightOut;
        } gs_in[]; 

        uniform mat4 ModelViewProjectionMatrix;
        uniform mat4 objectMatrix;
        uniform vec2 Viewport;
        uniform float thickness;
        uniform float extension;
        uniform float zOffset;
        uniform float weightInfluence;

        const float PI = 3.1415926;
        out vec2 mTexCoord;

        float width = thickness;
        float extAmount = extension * 0.01;
        vec4 vecOffset = vec4(0.0,0.0,zOffset,0.0);
        float radius = width;

        void main() {
            //calculate world space line normal and extension
            vec4 p1 =  gl_in[0].gl_Position;
            vec4 p2 =  gl_in[1].gl_Position;

            vec4 dir3d = vec4(normalize(p2.xyz-p1.xyz),0);

            vec4 p1ExtLocal = vec4(p1 - dir3d*extAmount);
            vec4 p2ExtLocal = vec4(p2 + dir3d*extAmount);


            // Project to Clip space Using Object and veiw matrix
            vec4 p1worldPos = objectMatrix * p1ExtLocal;
            vec4 p1project = ModelViewProjectionMatrix * p1worldPos;

            vec4 p2worldPos = objectMatrix * p2ExtLocal;
            vec4 p2project = ModelViewProjectionMatrix * p2worldPos;

            // Add Z offset
            vec4 p1Ext = p1project + vecOffset;
            vec4 p2Ext = p2project + vecOffset;

            // Get Screen Space points
            vec2 ssp1 = vec2(p1Ext.xy / p1Ext.w);
            vec2 ssp2 = vec2(p2Ext.xy / p2Ext.w);

            // Get Width per point
            float width1 = mix(width, gs_in[0].weightOut * width, weightInfluence);
            radius = width1;
            
            float width2 = mix(width, gs_in[1].weightOut * width, weightInfluence);
            


            // Screen Space direction and normal
            vec2 dir = normalize(ssp2 - ssp1);
            vec2 normal = vec2(-dir[1], dir[0]);
            normal = normalize(normal);

            // Screen Space line width offset
            vec2 lineOffset1 = vec2(normal * width1);
            lineOffset1.x /= Viewport.x;
            lineOffset1.y /= Viewport.y;


            vec2 lineOffset2 = vec2(normal * width2);
            lineOffset2.x /= Viewport.x;
            lineOffset2.y /= Viewport.y;

            

            // Generate the rectangle Coords
            vec4 coords[4];
            vec2 texCoords[4];

            coords[0] = vec4((ssp1 + lineOffset1)*p1Ext.w,p1Ext.z,p1Ext.w);
            texCoords[0] = vec2(0,1);

            coords[1] = vec4((ssp1 - lineOffset1)*p1Ext.w,p1Ext.z,p1Ext.w);
            texCoords[1] = vec2(0,0);

            coords[2] = vec4((ssp2 + lineOffset2)*p2Ext.w,p2Ext.z,p2Ext.w);
            texCoords[2] = vec2(0,1);

            coords[3] = vec4((ssp2 - lineOffset2)*p2Ext.w,p2Ext.z,p2Ext.w);
            texCoords[3] = vec2(0,0);



            // Draw Point pass
            // Get Center Point in Screen Space
            vec4 worldPos = objectMatrix * p1;
            vec4 project = ModelViewProjectionMatrix * worldPos;

            vec4 pointCenter = project + vecOffset;
            vec2 sspC = vec2(pointCenter.xy / pointCenter.w);

            // Get number of segments in the circle
            int segments = int(thickness) + 5;
            segments = clamp(segments,0,28);

            // Generate Circle
            gl_Position = pointCenter;
            mTexCoord = vec2(0,0.5);
            EmitVertex();

            for (int i = 0; i <= segments; i++) {
                // Angle between each side in radians
                float ang = PI * 2.0 / segments * i;

                // Offset from center of point
                vec2 circleOffset = vec2(cos(ang)*radius, -sin(ang)*radius);
                circleOffset.x /= Viewport.x;
                circleOffset.y /= Viewport.y;
                mTexCoord = vec2(0,1);
                gl_Position = vec4((sspC + circleOffset)*pointCenter.w, pointCenter.z, pointCenter.w);
                EmitVertex();

                gl_Position = pointCenter;
                mTexCoord = vec2(0,0.5);
                EmitVertex();
            }

            EndPrimitive();


            // Draw Rectange
            for (int i = 0; i < 4; ++i) {
                mTexCoord = texCoords[i];
                gl_Position = coords[i];
                EmitVertex();
            }
            EndPrimitive();
        }  
    '''

class Frag_Shaders_3D_B283 ():
    base_fragment_shader = '''
        uniform vec4 finalColor;
        out vec4 fragColor;

        void main()
        {
            fragColor = blender_srgb_to_framebuffer_space(finalColor);
        }
    '''
    
    aa_fragment_shader = '''
        in vec2 mTexCoord;
        in vec4 fcolor;
        in vec4 gl_FragCoord;
        uniform vec4 finalColor;
        uniform bool depthPass;
        out vec4 fragColor;

        void main()
        {
            vec4 aaColor = finalColor;
            vec4 mixColor = vec4(finalColor[0],finalColor[1],finalColor[2],0);

            vec2 center = vec2(0,0.5);
            float dist = length(mTexCoord - center);
            float distFromEdge = 1-(dist*2);

            float delta = fwidth(distFromEdge);
            float threshold = 1.5 * delta;
            float aa = clamp((distFromEdge/threshold)+0.5,0,1);
            aa = smoothstep(0,1,aa*aa);

            aaColor = mix(mixColor,finalColor,aa);

            if(depthPass){
                if (aa<1){
                    discard;
                }
            }
            
            fragColor = blender_srgb_to_framebuffer_space(aaColor); 
        }
    '''

    dashed_fragment_shader = '''
        in vec2 mTexCoord;
        uniform float u_Scale;
        uniform vec4 finalColor;
        uniform float dashSpace;
        
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
            
            float mapdashSpace = 2*dashSpace - 1;
            if (step(sin(g_ArcLength * u_Scale), mapdashSpace) == 1) discard;
            fragColor = blender_srgb_to_framebuffer_space(aaColor);
        }
    '''

    text_fragment_shader = '''
        uniform sampler2D image;

        in vec2 uvInterp;
        out vec4 fragColor;

        void main()
        {   
            vec4 color = texture(image, uvInterp);
            if (color[3]<0.1){
                discard;
            }
            fragColor = blender_srgb_to_framebuffer_space(color);
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
        uniform float dashSpace;
        
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
            
            float mapdashSpace = 2*dashSpace - 1;
            if (step(sin(g_ArcLength * u_Scale), mapdashSpace) == 1) discard;
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
            mTexCoord = vec2(0,0.5);
            EmitVertex();
            
            segments = clamp(segments,0,24);
            for (int i = 0; i <= segments; i++) {
                // Angle between each side in radians
                float ang = PI * 2.0 / segments * i;

                // Offset from center of point
                vec2 offset = vec2(cos(ang)*radius, -sin(ang)*radius);
                offset.x /= aspect;
                mTexCoord = vec2(0,1);
                gl_Position = vec4((ssp1 + offset)*p1.w,p1.z,p1.w);
                EmitVertex();

                gl_Position = gl_in[0].gl_Position;
                mTexCoord = vec2(0,0.5);
                EmitVertex();

            }

            EndPrimitive();
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
            vec4 color = texture(image, uvInterp);
            if (color[3]<0.1){
                discard;
            }
            fragColor = color;
        }
    '''

class DepthOnlyFrag():
    fragment_shader = ''' 
        uniform mat4 ModelViewProjectionMatrix;
        out vec4 fragColor;

        void main()
        {   
            float depth = gl_FragCoord.z;
            fragColor = vec4(depth, depth, depth, 1.0);
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