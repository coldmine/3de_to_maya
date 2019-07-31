#
#
# 3DE4.script.name:    Export Maya 75mm v2...
#
# 3DE4.script.version:    v2.5
#
# 3DE4.script.gui:    Main Window::3DE4::Export Project
# 3DE4.script.gui:    Main Window::75mm Studio Dev
#
# 3DE4.script.comment:    Creates a MEL script file that contains all project data, which can be imported into Autodesk Maya.
#
#

#
# import sdv's python vector lib...

from vl_sdv import *
import __builtin__ as builtin

import os
import re
import time
import tempfile
import subprocess
import multiprocessing
from itertools import islice
from functools import partial




#
# functions...


def convertToAngles(r3d):
    rot    = rot3d(mat3d(r3d)).angles(VL_APPLY_ZXY)
    rx    = (rot[0]*180.0)/3.141592654
    ry    = (rot[1]*180.0)/3.141592654
    rz    = (rot[2]*180.0)/3.141592654
    return(rx,ry,rz)


def convertZup(p3d,yup,scale):
    if yup==1:
        return([p3d[0]*scale,p3d[1]*scale,p3d[2]*scale])
    else:
        return([p3d[0]*scale,-p3d[2]*scale,p3d[1]*scale])


def angleMod360(d0,d):
    dd    = d-d0
    if dd>180.0:
        d    = angleMod360(d0,d-360.0)
    else:
        if dd<-180.0:
            d    = angleMod360(d0,d+360.0)
    return d


def validName(name):
    name    = name.replace(" ","_")
    name    = name.replace("'","_")
    name    = name.replace("\"","_")
    name    = name.replace("-","_")

    name    = name.replace("#","_")
    name    = name.replace(".","_")
    name    = name.replace("\n","")
    name    = name.replace("\r","")
    return name

def prepareImagePath(path,startframe):
    path    = path.replace("\\","/")
    i    = 0
    n    = 0
    i0    = -1
    while(i<builtin.len(path)):
        if path[i]=='#': n += 1
        if n==1: i0 = i
        i    += 1
    if i0!=-1:
        fstring        = "%%s%%0%dd%%s"%(n)
        path2        = fstring%(path[0:i0],startframe,path[i0+n:len(path)])
        path        = path2
    return path
def _maya_export_material(camera,pg,model,f):
    name = validName(tde4.get3DModelName(pg,model))
    f.write("string $myBlinn = `shadingNode -asShader blinn`;\n")
    f.write("select %s;\n"%name)
    f.write("hyperShade -assign $myBlinn;\n")
    f.write("string $file_shader = `shadingNode -asTexture -isColorManaged file`;\n")
    f.write("string $place2dtex = `shadingNode -asUtility place2dTexture`;\n")
    f.write("connectAttr -f ($place2dtex + \".coverage\") ($file_shader + \".coverage\");\n")
    f.write("connectAttr -f ($place2dtex + \".translateFrame\") ($file_shader + \".translateFrame\");\n")
    f.write("connectAttr -f ($place2dtex + \".rotateFrame\") ($file_shader + \".rotateFrame\");\n")
    f.write("connectAttr -f ($place2dtex + \".mirrorU\") ($file_shader + \".mirrorU\");\n")
    f.write("connectAttr -f ($place2dtex + \".mirrorV\") ( $file_shader + \".mirrorV\");\n")
    f.write("connectAttr -f ($place2dtex + \".stagger\") ( $file_shader + \".stagger\");\n")
    f.write("connectAttr -f ($place2dtex + \".wrapU\") ( $file_shader + \".wrapU\");\n")
    f.write("connectAttr -f ($place2dtex + \".wrapV\") ( $file_shader + \".wrapV\");\n")
    f.write("connectAttr -f ($place2dtex + \".repeatUV\") ( $file_shader + \".repeatUV\");\n")
    f.write("connectAttr -f ($place2dtex + \".offset\") ( $file_shader + \".offset\");\n")
    f.write("connectAttr -f ($place2dtex + \".rotateUV\") ( $file_shader + \".rotateUV\");\n")
    f.write("connectAttr -f ($place2dtex + \".noiseUV\") ( $file_shader + \".noiseUV\");\n")
    f.write("connectAttr -f ($place2dtex + \".vertexUvOne\") ( $file_shader + \".vertexUvOne\");\n")
    f.write("connectAttr -f ($place2dtex + \".vertexUvTwo\") ( $file_shader + \".vertexUvTwo\");\n")
    f.write("connectAttr -f ($place2dtex + \".vertexUvThree\") ( $file_shader + \".vertexUvThree\");\n")
    f.write("connectAttr -f ($place2dtex + \".vertexCameraOne\") ( $file_shader + \".vertexCameraOne\");\n")
    f.write("connectAttr ($place2dtex + \".outUV\") ( $file_shader + \".uv\");\n")
    f.write("connectAttr ($place2dtex + \".outUvFilterSize\") ( $file_shader + \".uvFilterSize\");\n")
    f.write("defaultNavigation -force true -connectToExisting -source $file_shader -destination ($myBlinn + \".color\");\n")
    f.write("window -e -vis false createRenderNodeWindow;\n")
    tpath = tde4.get3DModelUVTextureMap(pg,model)
    tpath = tpath.replace("\\","\\\\")
    f.write("setAttr -type \"string\" ($file_shader + \".fileTextureName\") \"%s\";\n"%(tpath))

def _maya_animate_model(f,camera,pg,cam,model,yup,unit_scale_factor):
    frames = tde4.getCameraNoFrames(cam)
    mesh_name = validName(tde4.get3DModelName(pg,model))
    for frame in builtin.range(1,frames+1):
        nvert = tde4.get3DModelNoVertices(pg,model)
        for vertex_index in builtin.range(0,nvert):
            p3d = tde4.get3DModelVertex(pg,model,vertex_index,cam,frame)
            p3d = convertZup(p3d,yup,unit_scale_factor)
            _maya_animate_vertex(f,mesh_name,vertex_index,frame,p3d)


def _maya_animate_vertex(f,mesh_name,vertex_index,frame,p3d):
    f.write("currentTime %i;\n"%(frame))
    f.write("select -r %s.vtx[%i] ;\n"%(mesh_name,vertex_index))
    f.write("move -a %15f %15f %15f;\n"%(p3d[0],p3d[1],p3d[2]))
    f.write("setKeyframe -breakdown 0 |Scene|%s|%s_shape.pnts[%i];\n"%(mesh_name,mesh_name,vertex_index))
    f.write("setKeyframe -breakdown 0 -hierarchy none -controlPoints 0 -shape 0 {\"%s.vtx[%i]\"};\n"%(mesh_name,vertex_index))

def _maya_export_model(camera,pg,model,f,export_material,yup,unit_scale_factor,index):
    if tde4.get3DModelReferenceFlag(pg,model) == 1:
        mname = validName(tde4.get3DModelName(pg,model))
        fpath = tde4.get3DModelFilepath(pg,model)
        fpath = fpath.replace("\\","\\\\")
        f.write("file -r -type \"OBJ\"  -ignoreVersion -gl -mergeNamespacesOnClash false -namespace \"%s\" -options \"mo=1\" \"%s\";\n"%(mname,fpath))
        f.write("parent %s:Mesh Scene;\n"%(mname))
        return
    linesep = "\\n\" + \n"
    ident = "\t\t\""
    python_str = "import maya.OpenMaya as om" + linesep
    python_str += ident + "pa = om.MPointArray()" + linesep
    nvert = tde4.get3DModelNoVertices(pg,model)
    frame = 1
    for i in builtin.range(0,nvert):
        p3d = tde4.get3DModelVertex(pg,model,i,camera,frame)
        p3d = convertZup(p3d,yup,unit_scale_factor)
        python_str += ident + "pa.append(%15f,%15f,%15f)"%(p3d[0],p3d[1],p3d[2]) + linesep

    python_str += ident + "poly_count = om.MIntArray()" + linesep
    faces = tde4.get3DModelNoFaces(pg,model)
    for i in builtin.range(0,faces):
        npoly = builtin.len(tde4.get3DModelFaceVertexIndices(pg,model,i))
        python_str += ident + "poly_count.append(%i)"%(npoly) + linesep

    python_str += ident + "poly_conn = om.MIntArray()" + linesep
    for i in builtin.range(0,faces):
        conn_list = tde4.get3DModelFaceVertexIndices(pg,model,i)
        for item in conn_list:
            python_str += ident + "poly_conn.append(%i)"%(item) + linesep

    python_str += ident + "u = om.MFloatArray()" + linesep
    python_str += ident + "v = om.MFloatArray()" + linesep
    python_str += ident + "uv_count = om.MIntArray()" + linesep
    python_str += ident + "uv_id = om.MIntArray()" + linesep
    uvid = 0
    for i in builtin.range(0,faces):
        max_v = builtin.len(tde4.get3DModelFaceVertexIndices(pg,model,i))
        python_str += ident + "uv_count.append(%i)"%(max_v) + linesep
        for v in builtin.range(0,max_v):
            u,v = tde4.get3DModelFaceUVCoord(pg,model,i,v)
            python_str += ident + "u.append(%15f)"%u + linesep
            python_str += ident + "v.append(%15f)"%v + linesep

            python_str += ident + "uv_id.append(%i)"%(uvid) + linesep
            uvid += 1

    python_str += ident + "obj = om.MFnMesh()" + linesep
    python_str += ident + "obj.create(%i,%i,pa,poly_count,poly_conn,u,v)"%(nvert,faces) + linesep
    python_str += ident + "obj.assignUVs(uv_count,uv_id)" + linesep
    name = validName(tde4.get3DModelName(pg,model))
    python_str += ident + "obj.setName(\\\"%s_shape\\\")"%(name) + linesep
    python_str += ident + "om.MFnDagNode(obj.parent(0)).setName(\\\"%s\\\")"%(name) + linesep
    python_str += ident + "selectionList = om.MSelectionList()" + linesep

    parent_name = "Scene"
    if tde4.getPGroupType(pg)=="OBJECT" and camera!=None:
                    parent_name    = "objectPGroup_%s_%d_1"%(validName(tde4.getPGroupName(pg)),index)

    python_str += ident + "selectionList.add( \\\"%s\\\" )"%parent_name + linesep
    python_str += ident + "node = om.MObject()" + linesep
    python_str += ident + "selectionList.getDependNode( 0, node )" + linesep
    python_str += ident + "om.MFnDagNode(node).fullPathName()" + linesep
    python_str += ident + "om.MFnDagNode(node).addChild(obj.parent(0))" + linesep
    python_str += ident + "transformFn = om.MFnTransform( obj.parent(0) )" + linesep
    p3d = tde4.get3DModelPosition3D(pg,model,camera,1)
    p3d = convertZup(p3d,yup,unit_scale_factor)
    r3d = tde4.get3DModelRotationScale3D(pg,model)
    python_str += ident + "matrix_content = [%15f , %15f, %15f, 0,%15f , %15f, %15f, 0,%15f , %15f, %15f, 0,%15f,%15f,%15f,1]"%(r3d[0][0], r3d[1][0],r3d[2][0],r3d[0][1],r3d[1][1],r3d[2][1],r3d[0][2],r3d[1][2],r3d[2][2],p3d[0],p3d[1],p3d[2]) + linesep

    python_str += ident + "import maya.cmds as cmds" + linesep
    python_str += ident + "cmds.select(\\\"%s|\\\" + om.MFnDagNode(obj.parent(0)).name())"%(parent_name) + linesep
    python_str += ident + "cmds.xform(matrix=matrix_content)" + linesep
    f.write("python (\"%s\"\");"%python_str)
    if export_material:
        _maya_export_material(camera,pg,model,f)

def _is_LD_default(camera):
    lens = tde4.getCameraLens(camera)
    lens_model = tde4.getLensLDModel(lens)

    seqDur = tde4.getCameraNoFrames(camera)
    parameterSize = tde4.getLDModelNoParameters(lens_model)

    for i in range(1, seqDur+1):
        focal_length = tde4.getCameraFocalLength(camera, i)
        focus_distance = tde4.getCameraFocus(camera, i)
        for j in range(0, parameterSize):
            para_name = tde4.getLDModelParameterName(lens_model, j)
            para_val = tde4.getLensLDAdjustableParameter(lens, para_name, focal_length, focus_distance)
            para_default = tde4.getLDModelParameterDefault(lens_model, para_name)
            if para_val != para_default:
                return False
    return True

#
# main script...


#
# search for camera point group...

campg    = None
pgl    = tde4.getPGroupList()
for pg in pgl:
    if tde4.getPGroupType(pg)=="CAMERA": campg = pg
if campg==None:
    tde4.postQuestionRequester("Export Maya...","Error, there is no camera point group.","Ok")
else:
    #
    # open requester...

    # Returns full path of 3de Project. If project is not saved, returns "None".
    tdePrjPath = tde4.getProjectPath() # /storage/show/studio75mm_190102_circle/scenes/S01/0010/hko/3de/S01_0010_v01_w01.3de
    try:
        tdePrjDir, tdePrjFile = os.path.split(tdePrjPath)
        jpgPlateDir = "{0}/plate/jpg".format(tdePrjDir.split(re.findall(r"/\w+/3de", tdePrjDir)[0])[0])
    except:
        pass

    if tdePrjPath is None: # If project is not saved...
        tde4.postQuestionRequester("Export Maya...", 'Save a project first!', 'Ok')
    else:
        req    = tde4.createCustomRequester()
        tde4.addFileWidget(req,"file_browser","Exportfile...","*.mel",tdePrjPath[:-3]+"mel") # "Mel Script Name" is current "3de Project Name"
        tde4.addTextFieldWidget(req, "startframe_field", "Startframe", "1")
        tde4.addOptionMenuWidget(req,"camera_selection","Export", "Current Camera Only", "Selected Cameras Only", "Sequence Cameras Only", "Reference Cameras Only","All Cameras")
        tde4.setWidgetValue(req,"camera_selection","5")
        tde4.addToggleWidget(req,"hide_ref_frames","Hide Reference Frames",0)
        tde4.addOptionMenuWidget(req,"model_selection","Export", "No 3D Models At All", "Selected 3D Models Only", "All 3D Models")
        tde4.setWidgetValue(req,"model_selection","3")
        tde4.addToggleWidget(req,"export_texture","Export UV Textures",0)
        tde4.addTextFieldWidget(req,"export_overscan_width_percent","Overscan Width %","100")
        tde4.addTextFieldWidget(req,"export_overscan_height_percent","Overscan Height %","100")
        #tde4.setWidgetValue(req,"model_selection","1")
        tde4.addOptionMenuWidget(req,"units","Units","cm", "m", "mm","in","ft","yd")

        tde4.addSeparatorWidget(req, 'sep01') #######################################

        tde4.addToggleWidget(req,"export_jpg","Export JPG", 0)

        cam    = tde4.getCurrentCamera()
        offset    = tde4.getCameraFrameOffset(cam)

        tde4.setWidgetValue(req, "startframe_field", builtin.str(tde4.getCameraSequenceAttr(cam)[0])) # Startframe Value same as Sequence In Frame.

        ## Export JPG Auto Toggle ##
        if _is_LD_default(cam) == False or os.path.isdir(jpgPlateDir) == True:
            tde4.setWidgetSensitiveFlag(req, "export_jpg", 0)
        else:
            tde4.setWidgetValue(req,"export_jpg", "1")

        ret    = tde4.postCustomRequester(req,"Export Maya 75mm Studio v2 (MEL-Script)...",700,0,"Ok","Cancel")
        if ret==1:
            camera_selection = tde4.getWidgetValue(req,"camera_selection")
            model_selection = tde4.getWidgetValue(req,"model_selection")

            overscan_w_pc = builtin.float(tde4.getWidgetValue(req,"export_overscan_width_percent"))/100.0
            overscan_h_pc = builtin.float(tde4.getWidgetValue(req,"export_overscan_height_percent"))/100.0
            export_material = tde4.getWidgetValue(req,"export_texture")
            camera_list = tde4.getCameraList()

            #1 : cm -> cm,2 : cm -> m, 3 : cm -> mm,4 : cm -> in,5 : cm -> ft,6 : cm -> yd
            unit_scales = {1 : 1.0,2 : 0.1,  3 : 10.0, 4 : 0.393701, 5 : 0.0328084, 6 : 0.0109361}
            unit_scale_factor = unit_scales[tde4.getWidgetValue(req,"units")]


            if camera_selection == 1:
                camera_list = [tde4.getCurrentCamera()]
            elif camera_selection == 2:
                camera_list = tde4.getCameraList(1)
            elif camera_selection == 3:
                camera_list = []
                tcl =  tde4.getCameraList()
                for c in tcl:
                    if tde4.getCameraType(c) == "SEQUENCE":
                        camera_list.append(c)
            elif camera_selection == 4:
                camera_list = []
                tcl =  tde4.getCameraList()
                for c in tcl:
                    if tde4.getCameraType(c) == "REF_FRAME":
                        camera_list.append(c)

            current_camera = tde4.getCurrentCamera()
            if builtin.len(camera_list) > 0:
                current_camera = camera_list[0]
            for c in camera_list:
                if c == tde4.getCurrentCamera():
                    current_camera = c

            # yup    = tde4.getWidgetValue(req,"mode_menu")
            # if yup==2: yup = 0
            yup    = 1
            path    = tde4.getWidgetValue(req,"file_browser")
            frame0    = builtin.float(tde4.getWidgetValue(req,"startframe_field"))
            frame0    -= 1
            hide_ref= tde4.getWidgetValue(req,"hide_ref_frames")
            if path!=None:
                if not path.endswith('.mel'): path = path+'.mel'
                f    = builtin.open(path,"w")
                if not f.closed:

                    #
                    # write some comments...

                    f.write("//\n")
                    f.write("// Maya/MEL export data written by %s\n"%tde4.get3DEVersion())
                    f.write("//\n")
                    f.write("// All lengths are in centimeter, all angles are in degree.\n")
                    f.write("//\n\n")

                    #
                    # write scene group...

                    f.write("// create scene group...\n")
                    f.write("string $sceneGroupName = `group -em -name \"Scene\"`;\n")

                    #
                    # write cameras...

                    index    = 1
                    for cam in camera_list:
                        camType        = tde4.getCameraType(cam)
                        noframes    = tde4.getCameraNoFrames(cam)
                        lens        = tde4.getCameraLens(cam)
                        if lens!=None:
                            name        = validName(tde4.getCameraName(cam))
                            name        = "%s_%s_1"%(name,index)
                            index        += 1
                            fback_w        = tde4.getLensFBackWidth(lens)
                            fback_h        = tde4.getLensFBackHeight(lens)
                            p_aspect    = tde4.getLensPixelAspect(lens)
                            focal        = tde4.getCameraFocalLength(cam,1)
                            lco_x        = tde4.getLensLensCenterX(lens)
                            lco_y        = tde4.getLensLensCenterY(lens)

                            # convert filmback to inch...
                            fback_w        = fback_w/2.54*overscan_w_pc
                            fback_h        = fback_h/2.54*overscan_h_pc
                            lco_x        = -lco_x/2.54*overscan_w_pc
                            lco_y        = -lco_y/2.54*overscan_h_pc

                            # convert focal length to mm...
                            focal        = focal*10.0


                            # create camera...
                            f.write("\n")
                            f.write("// create camera %s...\n"%name)
                            f.write("string $cameraNodes[] = `camera -name \"%s\" -hfa %.15f  -vfa %.15f -fl %.15f -ncp 0.01 -fcp 10000 -shutterAngle 180 -ff \"overscan\"`;\n"%(name,fback_w,fback_h,focal))
                            f.write("string $cameraTransform = $cameraNodes[0];\n")
                            f.write("string $cameraShape = $cameraNodes[1];\n")
                            f.write("xform -zeroTransformPivots -rotateOrder zxy $cameraTransform;\n")
                            f.write("setAttr ($cameraShape+\".horizontalFilmOffset\") %.15f;\n"%lco_x);
                            f.write("setAttr ($cameraShape+\".verticalFilmOffset\") %.15f;\n"%lco_y);
                            p3d    = tde4.getPGroupPosition3D(campg,cam,1)
                            p3d    = convertZup(p3d,yup,unit_scale_factor)
                            f.write("xform -translation %.15f %.15f %.15f $cameraTransform;\n"%(p3d[0],p3d[1],p3d[2]))
                            r3d    = tde4.getPGroupRotation3D(campg,cam,1)
                            rot    = convertToAngles(r3d)
                            f.write("xform -rotation %.15f %.15f %.15f $cameraTransform;\n"%rot)
                            f.write("xform -scale 1 1 1 $cameraTransform;\n")

                            # image plane...
                            f.write("\n")
                            f.write("// create image plane...\n")
                            f.write("string $myImagePlane[] = `imagePlane -camera $cameraTransform` ;\n")
                            f.write("setAttr ($myImagePlane[1] + \".offsetX\") %.15f;\n"%lco_x)
                            f.write("setAttr ($myImagePlane[1] + \".offsetY\") %.15f;\n"%lco_y)

                            if camType=="SEQUENCE": f.write("setAttr ($myImagePlane[1]+\".useFrameExtension\") 1;\n")
                            else:            f.write("setAttr ($myImagePlane[1]+\".useFrameExtension\") 0;\n")

                            f.write("expression -n \"frame_ext_expression\" -s ($myImagePlane[1]+\".frameExtension=frame\");\n")
                            path    = tde4.getCameraPath(cam)
                            sattr    = tde4.getCameraSequenceAttr(cam)
                            path    = prepareImagePath(path,sattr[0])
                            f.write("setAttr ($myImagePlane[1] + \".imageName\") -type \"string\" \"%s\";\n"%(path))
                            f.write("setAttr ($myImagePlane[1] + \".fit\") 4;\n")
                            f.write("setAttr ($myImagePlane[1] + \".displayOnlyIfCurrent\") 1;\n")
                            f.write("setAttr ($myImagePlane[1]  + \".depth\") (9000/2);\n")

                            # parent camera to scene group...
                            f.write("\n")
                            f.write("// parent camera to scene group...\n")
                            f.write("parent $cameraTransform $sceneGroupName;\n")

                            if camType=="REF_FRAME" and hide_ref:
                                f.write("setAttr ($cameraTransform +\".visibility\") 0;\n")

                            # animate camera...
                            if camType!="REF_FRAME":
                                f.write("\n")
                                f.write("// animating camera %s...\n"%name)
                                f.write("playbackOptions -min %d -max %d;\n"%(1+frame0,noframes+frame0))
                                f.write("\n")

                            frame    = 1
                            while frame<=noframes:
                                # rot/pos...
                                p3d    = tde4.getPGroupPosition3D(campg,cam,frame)
                                p3d    = convertZup(p3d,yup,unit_scale_factor)
                                r3d    = tde4.getPGroupRotation3D(campg,cam,frame)
                                rot    = convertToAngles(r3d)
                                if frame>1:
                                    rot    = [ angleMod360(rot0[0],rot[0]), angleMod360(rot0[1],rot[1]), angleMod360(rot0[2],rot[2]) ]
                                rot0    = rot
                                f.write("setKeyframe -at translateX -t %d -v %.15f $cameraTransform; \n"%(frame+frame0,p3d[0]))
                                f.write("setKeyframe -at translateY -t %d -v %.15f $cameraTransform; \n"%(frame+frame0,p3d[1]))
                                f.write("setKeyframe -at translateZ -t %d -v %.15f $cameraTransform; \n"%(frame+frame0,p3d[2]))
                                f.write("setKeyframe -at rotateX -t %d -v %.15f $cameraTransform; \n"%(frame+frame0,rot[0]))
                                f.write("setKeyframe -at rotateY -t %d -v %.15f $cameraTransform; \n"%(frame+frame0,rot[1]))
                                f.write("setKeyframe -at rotateZ -t %d -v %.15f $cameraTransform; \n"%(frame+frame0,rot[2]))

                                # focal length...
                                focal    = tde4.getCameraFocalLength(cam,frame)
                                focal    = focal*10.0
                                f.write("setKeyframe -at focalLength -t %d -v %.15f $cameraShape;\n"%(frame+frame0,focal))

                                frame    += 1

                    #
                    # write camera point group...

                    f.write("\n")
                    f.write("// create camera point group...\n")
                    name    = "cameraPGroup_%s_1"%validName(tde4.getPGroupName(campg))
                    f.write("string $pointGroupName = `group -em -name  \"%s\" -parent $sceneGroupName`;\n"%name)
                    f.write("$pointGroupName = ($sceneGroupName + \"|\" + $pointGroupName);\n")
                    f.write("\n")

                    # write points...
                    l    = tde4.getPointList(campg)
                    for p in l:
                        if tde4.isPointCalculated3D(campg,p):
                            name    = tde4.getPointName(campg,p)
                            name    = "p%s"%validName(name)
                            p3d    = tde4.getPointCalcPosition3D(campg,p)
                            p3d    = convertZup(p3d,yup,unit_scale_factor)
                            f.write("\n")
                            f.write("// create point %s...\n"%name)
                            f.write("string $locator = stringArrayToString(`spaceLocator -name %s`, \"\");\n"%name)
                            f.write("$locator = (\"|\" + $locator);\n")
                            f.write("xform -t %.15f %.15f %.15f $locator;\n"%(p3d[0],p3d[1],p3d[2]))
                            f.write("parent $locator $pointGroupName;\n")

                    f.write("\n")
                    f.write("xform -zeroTransformPivots -rotateOrder zxy -scale 1.000000 1.000000 1.000000 $pointGroupName;\n")
                    f.write("\n")


                    #
                    # write object/mocap point groups...

                    camera        = current_camera
                    noframes    = tde4.getCameraNoFrames(camera)
                    pgl        = tde4.getPGroupList()
                    index        = 1
                    for pg in pgl:
                        if tde4.getPGroupType(pg)=="OBJECT" and camera!=None:
                            f.write("\n")
                            f.write("// create object point group...\n")
                            pgname    = "objectPGroup_%s_%d_1"%(validName(tde4.getPGroupName(pg)),index)
                            index    += 1
                            f.write("string $pointGroupName = `group -em -name  \"%s\" -parent $sceneGroupName`;\n"%pgname)
                            f.write("$pointGroupName = ($sceneGroupName + \"|\" + $pointGroupName);\n")

                            # write points...
                            l    = tde4.getPointList(pg)
                            for p in l:
                                if tde4.isPointCalculated3D(pg,p):
                                    name    = tde4.getPointName(pg,p)
                                    name    = "p%s"%validName(name)
                                    p3d    = tde4.getPointCalcPosition3D(pg,p)
                                    p3d    = convertZup(p3d,yup,unit_scale_factor)
                                    f.write("\n")
                                    f.write("// create point %s...\n"%name)
                                    f.write("string $locator = stringArrayToString(`spaceLocator -name %s`, \"\");\n"%name)
                                    f.write("$locator = (\"|\" + $locator);\n")
                                    f.write("xform -t %.15f %.15f %.15f $locator;\n"%(p3d[0],p3d[1],p3d[2]))
                                    f.write("parent $locator $pointGroupName;\n")

                            f.write("\n")
                            scale    = tde4.getPGroupScale3D(pg)
                            f.write("xform -zeroTransformPivots -rotateOrder zxy -scale %.15f %.15f %.15f $pointGroupName;\n"%(scale,scale,scale))

                            # animate object point group...
                            f.write("\n")
                            f.write("// animating point group %s...\n"%pgname)
                            frame    = 1
                            while frame<=noframes:
                                # rot/pos...
                                p3d    = tde4.getPGroupPosition3D(pg,camera,frame)
                                p3d    = convertZup(p3d,yup,unit_scale_factor)
                                r3d    = tde4.getPGroupRotation3D(pg,camera,frame)
                                rot    = convertToAngles(r3d)
                                if frame>1:
                                    rot    = [ angleMod360(rot0[0],rot[0]), angleMod360(rot0[1],rot[1]), angleMod360(rot0[2],rot[2]) ]
                                rot0    = rot
                                f.write("setKeyframe -at translateX -t %d -v %.15f $pointGroupName; \n"%(frame+frame0,p3d[0]))
                                f.write("setKeyframe -at translateY -t %d -v %.15f $pointGroupName; \n"%(frame+frame0,p3d[1]))
                                f.write("setKeyframe -at translateZ -t %d -v %.15f $pointGroupName; \n"%(frame+frame0,p3d[2]))
                                f.write("setKeyframe -at rotateX -t %d -v %.15f $pointGroupName; \n"%(frame+frame0,rot[0]))
                                f.write("setKeyframe -at rotateY -t %d -v %.15f $pointGroupName; \n"%(frame+frame0,rot[1]))
                                f.write("setKeyframe -at rotateZ -t %d -v %.15f $pointGroupName;\n"%(frame+frame0,rot[2]))

                                frame    += 1

                        # mocap point groups...
                        if tde4.getPGroupType(pg)=="MOCAP" and camera!=None:
                            f.write("\n")
                            f.write("// create mocap point group...\n")
                            pgname    = "objectPGroup_%s_%d_1"%(validName(tde4.getPGroupName(pg)),index)
                            index    += 1
                            f.write("string $pointGroupName = `group -em -name  \"%s\" -parent $sceneGroupName`;\n"%pgname)
                            f.write("$pointGroupName = ($sceneGroupName + \"|\" + $pointGroupName);\n")

                            # write points...
                            l    = tde4.getPointList(pg)
                            for p in l:
                                if tde4.isPointCalculated3D(pg,p):
                                    name    = tde4.getPointName(pg,p)
                                    name    = "p%s"%validName(name)
                                    p3d    = tde4.getPointMoCapCalcPosition3D(pg,p,camera,1)
                                    p3d    = convertZup(p3d,yup,unit_scale_factor)
                                    f.write("\n")
                                    f.write("// create point %s...\n"%name)
                                    f.write("string $locator = stringArrayToString(`spaceLocator -name %s`, \"\");\n"%name)
                                    f.write("$locator = (\"|\" + $locator);\n")
                                    f.write("xform -t %.15f %.15f %.15f $locator;\n"%(p3d[0],p3d[1],p3d[2]))
                                    for frame in builtin.range(1,noframes+1):
                                        p3d    = tde4.getPointMoCapCalcPosition3D(pg,p,camera,frame)
                                        p3d    = convertZup(p3d,yup,unit_scale_factor)
                                        f.write("setKeyframe -at translateX -t %d -v %.15f $locator; \n"%(frame+frame0,p3d[0]))
                                        f.write("setKeyframe -at translateY -t %d -v %.15f $locator; \n"%(frame+frame0,p3d[1]))
                                        f.write("setKeyframe -at translateZ -t %d -v %.15f $locator; \n"%(frame+frame0,p3d[2]))
                                    f.write("parent $locator $pointGroupName;\n")

                            f.write("\n")
                            scale    = tde4.getPGroupScale3D(pg)
                            f.write("xform -zeroTransformPivots -rotateOrder zxy -scale %.15f %.15f %.15f $pointGroupName;\n"%(scale,scale,scale))

                            # animate mocap point group...
                            f.write("\n")
                            f.write("// animating point group %s...\n"%pgname)
                            frame    = 1
                            while frame<=noframes:
                                # rot/pos...
                                p3d    = tde4.getPGroupPosition3D(pg,camera,frame)
                                p3d    = convertZup(p3d,yup,unit_scale_factor)
                                r3d    = tde4.getPGroupRotation3D(pg,camera,frame)
                                rot    = convertToAngles(r3d)
                                if frame>1:
                                    rot    = [ angleMod360(rot0[0],rot[0]), angleMod360(rot0[1],rot[1]), angleMod360(rot0[2],rot[2]) ]
                                rot0    = rot
                                f.write("setKeyframe -at translateX -t %d -v %.15f $pointGroupName; \n"%(frame+frame0,p3d[0]))
                                f.write("setKeyframe -at translateY -t %d -v %.15f $pointGroupName; \n"%(frame+frame0,p3d[1]))
                                f.write("setKeyframe -at translateZ -t %d -v %.15f $pointGroupName; \n"%(frame+frame0,p3d[2]))
                                f.write("setKeyframe -at rotateX -t %d -v %.15f $pointGroupName; \n"%(frame+frame0,rot[0]))
                                f.write("setKeyframe -at rotateY -t %d -v %.15f $pointGroupName; \n"%(frame+frame0,rot[1]))
                                f.write("setKeyframe -at rotateZ -t %d -v %.15f $pointGroupName;\n"%(frame+frame0,rot[2]))

                                frame    += 1

                        model_list = []
                        if model_selection == 2:
                            model_list = tde4.get3DModelList(pg,1)
                        elif model_selection == 3:
                            model_list = tde4.get3DModelList(pg,0)
                        for model in model_list:
                            _maya_export_model(camera,pg,model,f,export_material,yup,unit_scale_factor,index-1)
                            if tde4.getPGroupType(pg)=="MOCAP" and camera!=None:
                                _maya_animate_model(f,camera,pg,camera,model,yup,unit_scale_factor)
                    #
                    # global (scene node) transformation...

                    p3d    = tde4.getScenePosition3D()
                    p3d    = convertZup(p3d,yup,unit_scale_factor)
                    r3d    = tde4.getSceneRotation3D()
                    rot    = convertToAngles(r3d)
                    s    = tde4.getSceneScale3D()
                    f.write("xform -zeroTransformPivots -rotateOrder zxy -translation %.15f %.15f %.15f -scale %.15f %.15f %.15f -rotation %.15f %.15f %.15f $sceneGroupName;\n\n"%(p3d[0],p3d[1],p3d[2],s,s,s,rot[0],rot[1],rot[2]))

                    f.write("\n")
                    f.close()

                    ## Export JPG Start ##
                    if tde4.getWidgetValue(req, "export_jpg") == 1:
                        if os.path.isdir(jpgPlateDir) == True: # /storage/show/studio75mm_190102_circle/scenes/S01/0010/plate/jpg Directory Exsits?
                            pass
                        else:
                            # Create "jpg" Directory
                            os.mkdir(jpgPlateDir)

                            # Input Sequence Info
                            inSeqDur = tde4.getCameraNoFrames(cam)

                            # Export JPG Sequence with oiiotool
                            commands = []
                            for i in range(1, inSeqDur+1):
                                inSeqPath = tde4.getCameraFrameFilepath(cam,i) # /storage/show/studio75mm_190102_circle/scenes/S01/0010/plate/dpx/S01_0010.0001.dpx
                                inSeqFile = os.path.basename(inSeqPath) # "S01_0010.0001.dpx"
                                inSeqRoot, inSeqExt = os.path.splitext(inSeqFile) # "S01_0010.1001" ".dpx"

                                outSeqPath = "{0}/{1}.jpg".format(jpgPlateDir, inSeqRoot) # /storage/show/studio75mm_190102_circle/scenes/S01/0010/plate/jpg/S01_0010.0001.jpg

                                commands.append("oiiotool {0} --threads 1 --quality 100 -v -o {1}".format(inSeqPath, outSeqPath)) # --sRGB

                            p = multiprocessing.Pool(multiprocessing.cpu_count()-1)

                            #start = time.time()

                            tde4.postProgressRequesterAndContinue("Exporting JPG Sequence...", "Exporting Frame 1", len(commands), "Stop")
                            for i, returncode in enumerate(p.imap(partial(subprocess.call, shell=True), commands)):
                                tde4.updateProgressRequester(i+1,"Exporting Frame {0}...".format(i+1))
                                if returncode != 0:
                                    print("%d command failed: %d" % (i, returncode))
                            tde4.unpostProgressRequester()

                            #print 'Time elapsed: %s' % (time.time() - start)

                    ## Export JPG End ##


                    ## Export Scene Metadata to Maya Start ##
                    shot = tdePrjFile.split(re.findall(r"_v\d{2}_w\d{2}", tdePrjPath)[0])[0]

                    ver = int(re.findall(r"_v\d{2}", tdePrjPath)[0][-2:]) # ex) _v01 >> 1
                    wip = 1

                    ## Image Sequence Details ##
                    IMAGE_WIDTH = tde4.getCameraImageWidth(cam)
                    IMAGE_HEIGHT = tde4.getCameraImageHeight(cam)

                    inSeqFirstFramePath = tde4.getCameraFrameFilepath(camera,1)
                    inSeqFirstFrameFile = os.path.basename(inSeqFirstFramePath)
                    inSeqFirstFrameRoot, inSeqFirstFrameExt =  os.path.splitext(inSeqFirstFrameFile)

                    outSeqFirstFramePath = "{0}/{1}.jpg".format(jpgPlateDir, inSeqFirstFrameRoot) # /storage/show/studio75mm_190102_circle/scenes/S01/0010/plate/jpg/S01_0010.0001.jpg
                    JPG_EXIST = os.path.isfile(outSeqFirstFramePath)

                    mayaPrjPath = "{0}/maya/{1}_v{2:02d}_w{3:02d}{4}".format(tdePrjDir.split('/3de')[0], shot, ver, wip, '.ma')
                    mayaPrjDir = "{0}/maya".format(tdePrjDir.split('/3de')[0])

                    with open(r"{0}/tde4_mel.txt".format(tempfile.gettempdir()),"w") as f:
                        f.write("{0} {1} {2} {3} {4} {5} {6}".format(tdePrjPath[:-3]+'mel', IMAGE_WIDTH, IMAGE_HEIGHT, JPG_EXIST, outSeqFirstFramePath, mayaPrjPath, mayaPrjDir))
                    ## Export Scene Metadata to Maya End ##

                    tde4.postQuestionRequester("Export Maya...","Project successfully exported.","Ok")
                else:
                    tde4.postQuestionRequester("Export Maya...","Error, couldn't open file.","Ok")
