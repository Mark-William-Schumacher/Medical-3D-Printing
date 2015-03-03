from __main__ import vtk
from __main__ import slicer
import numpy 
import math

class Util_HDR:
  def ShiftImageData(self, imageData, shiftAmount):
    """ Shift the image to an amount and ORs the shifts together
    PARAM-imageData = vtkImageData()
    PARAM shiftAmount = float corresponds to the thickness the plastic needs to be in the mould
    """
    prev = imageData
    for i in range(6):
      imagePadFilter= vtk.vtkImageConstantPad()
      extent        = imageData.GetExtent()
      print extent
      if (i % 2 == 0):
        extent = self.addToExtent(extent,i,-shiftAmount)
      else:
        extent = self.addToExtent(extent,i,+shiftAmount)
      print extent
      imagePadFilter.SetInputData(imageData)
      imagePadFilter.SetOutputWholeExtent(extent[0],extent[1],extent[2],extent[3],extent[4],extent[5])
      imagePadFilter.Update()
      if (i % 2 == 0):
        extent = self.addToExtent(extent,i+1,-shiftAmount)
      else:
        extent = self.addToExtent(extent,i-1,+shiftAmount)
      print extent
      extractVOI    = vtk.vtkExtractVOI()
      extractVOI.SetInputConnection(imagePadFilter.GetOutputPort())
      extractVOI.SetVOI(extent[0],extent[1],extent[2],extent[3],extent[4],extent[5])
      extractVOI.Update()
      if (i % 2 == 0):
        extent = self.addToExtent(extent,i,+shiftAmount)
        extent = self.addToExtent(extent,i+1,+shiftAmount)
      else:
        extent = self.addToExtent(extent,i,-shiftAmount)
        extent = self.addToExtent(extent,i-1,-shiftAmount)
      print extent
      extractVOI.GetOutput().SetExtent(extent[0],extent[1],extent[2],extent[3],extent[4],extent[5])
      temp = extractVOI.GetOutput()
      prev= self.ImageOR(temp, prev)
    return prev
  def addToExtent(self, extent , i , amount):
    """ Used in ShiftImageData as a helper function
    """
    temp=[extent[0],extent[1],extent[2],extent[3],extent[4],extent[5]]
    temp[i] = temp[i] + amount
    extent = (temp[0],temp[1],temp[2],temp[3],temp[4],temp[5])
    return extent
  def DilateImageData(self, imageData, numberOfDilations,dilateValue=0,errodeValue=255):
    """ 
    VERY EXPENSIVE, will dilate the current binary volume a number of times 
    anything over 10 dilations will take hours on a high voxel density volume
    This will dilate the 0(BYDEFAULT) value voxels and errode the 255(BYDEFAULT) value voxels
    x number of times, we assume uniform dilations in x,y,z.
    PARAM- vtkImageData()         remains unchanged
    PARAM- int                    number of voxel dilations
    PARAM- dilateValue            the region that will dilate (0 by default)
    PARAM- errodeValue            the region that will errode (255 by default)
    RETURN- vtkImageData          ImageData
    """
    dilationFilter=vtk.vtkImageDilateErode3D()
    dilationFilter.SetDilateValue(dilateValue)
    dilationFilter.SetErodeValue(errodeValue)
    dilationFilter.SetKernelSize(numberOfDilations,numberOfDilations,numberOfDilations)
    dilationFilter.SetInputData(imageData)
    dilationFilter.Update()
    return dilationFilter.GetOutput()
  def ImageNegation(self,imageData,referenceVolume):
    """ This function negates the image
    PARAM: imageData1 vtkImageData()
    PARAM: vtkMRMLScalarVolumeNode() referenceVolume 
    RETURN: vtkImageData()
    ASK ANDRAS IS THERE IS A BETTERWAY TO FLIP THE BINARY BITS
    """
    air             =   self.PolyDataToImageData(vtk.vtkPolyData(),referenceVolume,0,255)
    imageLogic= vtk.vtkImageLogic()
    imageLogic.SetOperationToXor()
    imageLogic.SetInput1Data(imageData) 
    imageLogic.SetInput2Data(air)
    imageLogic.Update()
    return imageLogic.GetOutput()
  def ImageAND(self,imageData1,imageData2):
    """ This function ANDs two image datas 
    PARAM: imageData1 vtkImageData()
    PARAM: imageData2 vtkImageData()
    RETURN: vtkImageData()
    """
    imageLogic= vtk.vtkImageLogic()
    imageLogic.SetOperationToAnd()
    imageLogic.SetInput1Data(imageData1) 
    imageLogic.SetInput2Data(imageData2)
    imageLogic.Update()
    return imageLogic.GetOutput()
  def ImageOR(self,imageData1,imageData2):
    """ This function ORs two image datas 
    PARAM: imageData1 vtkImageData()
    PARAM: imageData2 vtkImageData()
    RETURN: vtkImageData()
    """
    imageLogic= vtk.vtkImageLogic()
    imageLogic.SetOperationToOr()
    imageLogic.SetInput1Data(imageData1) 
    imageLogic.SetInput2Data(imageData2)
    imageLogic.Update()
    return imageLogic.GetOutput()
  def ImageXOR(self, imageData1, imageData2):
    """ This function XORs two image datas 
    PARAM: imageData1 vtkImageData()
    PARAM: imageData2 vtkImageData()
    RETURN: vtkImageData()
    """
    imageLogic= vtk.vtkImageLogic()
    imageLogic.SetOperationToXor()
    imageLogic.SetInput1Data(imageData1) 
    imageLogic.SetInput2Data(imageData2)
    imageLogic.Update()
    return imageLogic.GetOutput()
  def MergeAllImages(self, arrayOfImageData):
    """ This function will append all images by -or- operations from an 
    array of image data to create a single imaga data will all datas merged
    
    PARAM: Array of image data          Array< ImageData > 
    RETURN : vtkImageData
    """
    if (len(arrayOfImageData)==0):
      print "Warning: Empty array of Image Data"
      return None
    imageLogic= vtk.vtkImageLogic()
    imageLogic.SetOperationToOr()
    accumulator = arrayOfImageData.pop()   # Initialize the addition sequence
    while (0 < len(arrayOfImageData)): #Appends all previous images
      imageLogic.SetInput1Data(accumulator) 
      imageLogic.SetInput2Data(arrayOfImageData.pop()) #Appends Next tube
      imageLogic.Update()
      accumulator=(imageLogic.GetOutput())
    return accumulator
  def CreateVolumeFromRoi(self, roiNode, spacingMm):
    """Creates a volume node with image data of proper spacing inside of it
    PARAM : roi and spacing we wish to have
    RETURN : vtkMRMLScalarVolumeNode()
    """
    
    roiCenter = [0, 0, 0]
    roiNode.GetXYZ( roiCenter )
    roiRadius = [0, 0, 0]
    roiNode.GetRadiusXYZ( roiRadius )
    roiOrigin_Roi = [roiCenter[0] - roiRadius[0], roiCenter[1] - roiRadius[1], roiCenter[2] - roiRadius[2], 1 ]

    roiToRas = vtk.vtkMatrix4x4()
    if roiNode.GetTransformNodeID() != None:
      roiBoxTransformNode = slicer.mrmlScene.GetNodeByID(roiNode.GetTransformNodeID())
      roiBoxTransformNode.GetMatrixTransformToWorld(roiToRas)

    outputVolumeSize = [roiRadius[0]*2/spacingMm, roiRadius[1]*2/spacingMm, roiRadius[2]*2/spacingMm]
    outputVolumeSize = [int(math.ceil(x)) for x in outputVolumeSize]

    outputImageData = vtk.vtkImageData()
    outputImageData.SetExtent(0, outputVolumeSize[0]-1, 0, outputVolumeSize[1]-1, 0, outputVolumeSize[2]-1)
    if vtk.VTK_MAJOR_VERSION <= 5:
      outputImageData.SetScalarType(vtk.VTK_UNSIGNED_CHAR)
      outputImageData.SetNumberOfScalarComponents(3)
      outputImageData.AllocateScalars()
    else:
      outputImageData.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 1)
      
    outputVolumeNode = slicer.vtkMRMLScalarVolumeNode()
    outputVolumeNode.SetAndObserveImageData(outputImageData)
    outputVolumeNode.SetIJKToRASDirections( roiToRas.GetElement(0,0), roiToRas.GetElement(0,1), roiToRas.GetElement(0,2), roiToRas.GetElement(1,0), roiToRas.GetElement(1,1), roiToRas.GetElement(1,2), roiToRas.GetElement(2,0), roiToRas.GetElement(2,1), roiToRas.GetElement(2,2))
    outputVolumeNode.SetSpacing(spacingMm, spacingMm, spacingMm)
    roiOrigin_Ras = roiToRas.MultiplyPoint(roiOrigin_Roi)
    outputVolumeNode.SetOrigin(roiOrigin_Ras[0:3])
    return outputVolumeNode
  def PolyDataToImageData(self, inputPolydata_Ras, referenceVolumeNode_Ras, inVal=100, outVal=0):
    """ We take in an polydata and convert it to an new image data , withing the Reference Voulume node
        the reference volume node is cleared with a threshold because originally the volume may contain
        alot of noisy pixels 
        PARAM: inputPolydata_Ras: Polydata we are looking to conver       vtkPolydata()
        PARAM: refernceVolumeNode_Ras                                     vtkMRMLScalarVolumeNode()
        RETURN : vtkImageData
        """
    
    """ Transform the polydata from ras to ijk using the referenceVolumeNode """
    #inputPolydataTriangulated_Ijk=polyToImage.GetOutput()
    transformPolydataFilter=vtk.vtkTransformPolyDataFilter()
    rasToIjkMatrix=vtk.vtkMatrix4x4()
    referenceVolumeNode_Ras.GetRASToIJKMatrix(rasToIjkMatrix)
    rasToIjkTransform = vtk.vtkTransform()
    rasToIjkTransform.SetMatrix(rasToIjkMatrix)
    transformPolydataFilter.SetTransform(rasToIjkTransform)
    transformPolydataFilter.SetInputData(inputPolydata_Ras)
    transformPolydataFilter.Update()
    inputPolydata_Ijk=transformPolydataFilter.GetOutput()
    normalsFunction=vtk.vtkPolyDataNormals()
    normalsFunction.SetInputData(inputPolydata_Ijk)
    normalsFunction.ConsistencyOn()
    trigFilter=vtk.vtkTriangleFilter()
    trigFilter.SetInputConnection(normalsFunction.GetOutputPort())
    stripper=vtk.vtkStripper()
    stripper.SetInputConnection(trigFilter.GetOutputPort())
    stripper.Update()
    inputPolydataTriangulated_Ijk=stripper.GetOutput()
    
    # Clone reference image and clear it
    referenceImage_Ijk = referenceVolumeNode_Ras.GetImageData()
    
    # Fill image with outVal (there is no volume Fill filter in VTK, therefore we need to use threshold filter)
    thresh = vtk.vtkImageThreshold()
    thresh.ReplaceInOn()
    thresh.ReplaceOutOn()
    thresh.SetInValue(outVal)
    thresh.SetOutValue(outVal)
    #thresh.SetOutputScalarType (vtk.VTK_UNSIGNED_CHAR)
    thresh.SetInputData(referenceImage_Ijk)
    thresh.Update()
    whiteImage_Ijk = thresh.GetOutput()

    # Convert polydata to stencil
    polyToImage = vtk.vtkPolyDataToImageStencil()
    polyToImage.SetInputData(inputPolydataTriangulated_Ijk)
    polyToImage.SetOutputSpacing(whiteImage_Ijk.GetSpacing())
    polyToImage.SetOutputOrigin(whiteImage_Ijk.GetOrigin())
    polyToImage.SetOutputWholeExtent(whiteImage_Ijk.GetExtent())
    polyToImage.Update()
    imageStencil_Ijk=polyToImage.GetOutput()
    
    # Convert stencil to image
    imgstenc = vtk.vtkImageStencil()
    imgstenc.SetInputData(whiteImage_Ijk)
    imgstenc.SetStencilData(imageStencil_Ijk)
    imgstenc.ReverseStencilOn()
    imgstenc.SetBackgroundValue(inVal)
    imgstenc.Update()
    return imgstenc.GetOutput()
  def DisplayVolumeNode(self, volumeNode, name="Volume"):
    existingVolumeNode=slicer.util.getNode(name)
    if not existingVolumeNode:
      displayNode=slicer.vtkMRMLScalarVolumeDisplayNode()
      displayNode.SetAndObserveColorNodeID("vtkMRMLColorTableNodeGrey")
      volumeNode.SetName(name)
      slicer.mrmlScene.AddNode(volumeNode)
      slicer.mrmlScene.AddNode(displayNode)
      volumeNode.SetAndObserveDisplayNodeID(displayNode.GetID())
    else:
      existingVolumeNode.SetImageData(volumeNode.GetImageData())
      existingVolumeNode.SetIJKToRAS(volumeNode.GetIJKToRAS())
    return

  def DisplayImageData(self, imageData_Ijk, referenceVolumeNode_Ras, name="ImageNode"):
    volumeNode_Ras=slicer.util.getNode(name)
    if (not volumeNode_Ras):
      displayNode=slicer.vtkMRMLScalarVolumeDisplayNode()
      displayNode.SetAndObserveColorNodeID("vtkMRMLColorTableNodeGrey")
      volumeNode_Ras=slicer.vtkMRMLScalarVolumeNode()
      volumeNode_Ras.SetName(name)
      slicer.mrmlScene.AddNode(volumeNode_Ras)
      slicer.mrmlScene.AddNode(displayNode)
      volumeNode_Ras.SetAndObserveDisplayNodeID(displayNode.GetID())
    volumeNode_Ras.SetAndObserveImageData(imageData_Ijk)
    rasToIjkMatrix=vtk.vtkMatrix4x4()
    referenceVolumeNode_Ras.GetRASToIJKMatrix(rasToIjkMatrix)
    volumeNode_Ras.SetRASToIJKMatrix(rasToIjkMatrix)
    return volumeNode_Ras
  def GetMidPoint(self,p1,p2):
    """ Gets the midpoint between two points in space 
    """
    a,b,c=p1
    d,e,f=p2
    return ((a+d)/2,(b+e)/2,(c+f)/2)
  def PointsToPolyData(self,listOfPoints):
    """ Converts 3D list of points of an array into a polyData line
    The connections between this line are simply the order in which 
    they are provided
    """
    points=vtk.vtkPoints()
    idlist = vtk.vtkIdList()
    numOfPoints=len(listOfPoints)
    if numOfPoints==0:
      print ("WARNING:No points to convert to polyData")
      return vtk.vtkPolyData() #returning Blank PolyData
    points.SetNumberOfPoints(numOfPoints)
    for i in range (numOfPoints):
      points.InsertPoint(i, listOfPoints[i]) #Add the points
      idlist.InsertNextId(i)
    polyData=vtk.vtkPolyData()
    polyData.Allocate()
    polyData.InsertNextCell(vtk.VTK_LINE,idlist)
    polyData.SetPoints(points)
    return polyData
  def DisplayPoints(self, polyDataLine,name):
    """ Will display all of the points of a given Polydata Line
    """
    sphere= vtk.vtkSphereSource()
    sphere.SetRadius(0.3)
    sphere.Update()
    glyphFilter=vtk.vtkGlyph3D()
    glyphFilter.ScalingOff()
    glyphFilter.SetSourceData(sphere.GetOutput()) #object at eachPoint
    glyphFilter.SetInputData(polyDataLine)
    glyphFilter.Update()
    node=self.DisplayPolyData(name, glyphFilter.GetOutput())
    node.SetColor(0.3,0.4,1) #Max 1 for each column
    node.SetAmbient(1)
    return node
  def PolyDataWriter(self, polyData, path):
    """ Creates a vtk file for the given path
    The path must be a valid file location and name for the file
    .vtk is recommended to be at the end
    AVOID spaces in the filename and path
    """
    w = vtk.vtkPolyDataWriter()
    w.SetInputData(polyData)
    w.SetFileTypeToASCII()
    w.SetFileName(path)
    w.Write()
  def PolyDataToList(self,polyData):
    """ This won't work for all polyData
    """
    points=polyData.GetPoints() #vtkPoints
    numOfPoints=points.GetNumberOfPoints() #vtkPoints functions
    listOfPoints=[]
    for i in range(numOfPoints):
      listOfPoints.append(points.GetPoint(i))
    return listOfPoints  
  def DotProduct(self, v1, v2):
    v1a,v1b,v1c =v1[0],v1[1],v1[2]
    v2a,v2b,v2c =v2[0],v2[1],v2[2]
    return v1a*v2a+v1b*v2b+v1c*v2c
  def UnpackPoints(self, markupNode):
    """ Takes a node as given by the widgit and returns a python
    list of the points in R-A-S format.
    """
    numOfPlanes=markupNode.GetNumberOfFiducials()
    listOfPoints=[]
    for i in range(numOfPlanes):
      point=[0,0,0]# have to use a the C++ style of getter (see API)
      markupNode.GetNthFiducialPosition(i, point) #unpacking point
      listOfPoints.append(point)
    return listOfPoints
  def GetRulerVector(self, ruler):
    # x is L->R, y is P->A, z is I->S
    """ Takes ruler and returns a vector [x,y,z]
    x is L->R, y is P->A, z is I->S
    """
    position1=[0,0,0]
    position2=[0,0,0]
    ruler.GetPosition1(position1)
    ruler.GetPosition2(position2)
    return self.GetVector(position1, position2)
  def GetVector(self,point1,point2):
    """ Returns a vector given two points
    """
    vector=[0,0,0]
    for i in range(len(point1)):
      vector[i]=point2[i]-point1[i]
    return vector
  def CrossProduct(self,v1,v2):
    temp=[0,0,0]
    temp[0]=v1[1]*v2[2]-v1[2]*v2[1]
    temp[1]=v1[2]*v2[0]-v1[0]*v2[2]
    temp[2]=v1[0]*v2[1]-v1[1]*v2[0]
    return temp
  def CreateNewNode(self,nodeName, nodeType="vtkMRMLModelNode", overwrite=True):
      """Create new node from scratch
      """
      scene = slicer.mrmlScene
      newNode = scene.CreateNodeByClass(nodeType)
      newNode.UnRegister(scene)
      self.AddNodeToMRMLScene(newNode, nodeName, overwrite)
      return newNode
  def AddNodeToMRMLScene(self,newNode, nodeName='default', overwrite=True):
      scene = slicer.mrmlScene
      if not overwrite:
        nodeName = scene.GetUniqueNameByString(nodeName)
      newNode.SetName(nodeName)
      if overwrite:
        self.removeOldMRMLNode(newNode)
      scene.AddNode(newNode)
  def removeOldMRMLNode(self,node):
      """Overwrite a MRML node with the same name and class as the given node
      """
      scene = slicer.mrmlScene
      collection = scene.GetNodesByClassByName(node.GetClassName(), node.GetName())
      if collection.GetNumberOfItems() == 1:
        oldNode = collection.GetItemAsObject(0)
        scene.RemoveNode(oldNode)
      elif collection.GetNumberOfItems() > 1:
        # This should never happen
        raise Exception("Unable to determine node to replace! Too many existing.")
      else:
        # There was no node to overwrite
        return 1
      return 0
  def DisplayPolyData(self, nameOfNode, polyData, overwrite=True):
    """ Function that Overwrites/Creates a Node to display Polydata
    """
    n=self.CreateNewNode(nameOfNode, "vtkMRMLModelNode", overwrite=True)
    outputMouldModelDisplayNode = slicer.vtkMRMLModelDisplayNode()
    slicer.mrmlScene.AddNode(outputMouldModelDisplayNode)
    outputMouldModelDisplayNode.BackfaceCullingOff()
    n.SetAndObserveDisplayNodeID(outputMouldModelDisplayNode.GetID())
    n.SetAndObservePolyData(polyData)
    return outputMouldModelDisplayNode
  def TurnOffDisplay(self,name):
    """ will turn off whatever node name given from the display 
    """
    x=slicer.mrmlScene.GetNodesByName(name)
    y=x.GetItemAsObject(0)
    z=y.GetDisplayNode()
    if z==None:
      raise Exception ("No node named: " +name)
    z.SetVisibility(0)
  def DisplayImplicit(self,name,implicitFunction, ROI=None, Extents=None):
    """This function takes an implicitFunction and displays it within the ROI
    It will return the modelDisplaynode assosiated with in so that attributes 
    can be changed
    """
    sampleFunction=vtk.vtkSampleFunction()
    sampleFunction.SetSampleDimensions(70,70,70)
    sampleFunction.SetImplicitFunction(implicitFunction)
    ROIExtents=[0,0,0,0,0,0]
    if ROI==None:
      ROIExtents=Extents
    else:
      ROIExtents=self.GetROIExtents(ROI)
    sampleFunction.SetModelBounds(ROIExtents)
    sampleFunction.Update()
    contourFilter=vtk.vtkContourFilter()
    contourFilter.SetInputConnection(sampleFunction.GetOutputPort())
    contourFilter.GenerateValues(1,0,0)
    contourFilter.Update()
    polyData=contourFilter.GetOutput()
    modelDisplayNode=self.DisplayPolyData(name,polyData)
    return modelDisplayNode
  def ExpandExtents(self,ROIExtents, value):
    """ This Expands the ROIExtents which define a box, so it makes 
    the area larger by the passed in value
    """
    newROI=[0,0,0,0,0,0]
    evenNumber=True
    for index in range(len(ROIExtents)):
      if evenNumber==True:
        newROI[index]=ROIExtents[index]-value
        evenNumber=False
      else:
        newROI[index]=ROIExtents[index]+value
        evenNumber=True
    return newROI
  def GetROIExtents(self, ROI):
    """Returns the xmin, xmax, ymin, ymax,zmin,zmax of the ROI box
    """
    ROICenterPoint = [0,0,0]
    ROI.GetXYZ(ROICenterPoint)
    ROIRadii = [0,0,0]
    ROI.GetRadiusXYZ(ROIRadii)
    ROIExtents = [0,0,0,0,0,0]
    ROIExtents[0] = ROICenterPoint[0] - ROIRadii[0]
    ROIExtents[1] = ROICenterPoint[0] + ROIRadii[0]
    ROIExtents[2] = ROICenterPoint[1] - ROIRadii[1]
    ROIExtents[3] = ROICenterPoint[1] + ROIRadii[1]
    ROIExtents[4] = ROICenterPoint[2] - ROIRadii[2]
    ROIExtents[5] = ROICenterPoint[2] + ROIRadii[2]
    return ROIExtents
  def GetROIPoints(self,ROI):
    """ RAS 
    L->R  Index [0],[1]
    P->A  Index[2],[3]
    I->S  Index[4],[5]
    """
    ROICenterPoint = [0,0,0]
    ROI.GetXYZ(ROICenterPoint)
    ROIRadii = [0,0,0]
    ROI.GetRadiusXYZ(ROIRadii)
    ROIPoints=[]
    ROIPoints.append([ROICenterPoint[0]-ROIRadii[0],ROICenterPoint[1],ROICenterPoint[2]])
    ROIPoints.append([ROICenterPoint[0]+ROIRadii[0],ROICenterPoint[1],ROICenterPoint[2]])
    ROIPoints.append([ROICenterPoint[0],ROICenterPoint[1]-ROIRadii[1],ROICenterPoint[2]])
    ROIPoints.append([ROICenterPoint[0],ROICenterPoint[1]+ROIRadii[1],ROICenterPoint[2]])
    ROIPoints.append([ROICenterPoint[0],ROICenterPoint[1],ROICenterPoint[2]-ROIRadii[2]])
    ROIPoints.append([ROICenterPoint[0],ROICenterPoint[1],ROICenterPoint[2]+ROIRadii[2]])
    return ROIPoints
  def GetClosestExtent(self,ruler,ROI):
    """ Returns the index of the closest ROI Extent to the second point
    on the ruler. 
    Asserted that the second point of the ruler is closest to the front 
    extent of the ROI box.
    """
    roiPoints=self.GetROIPoints(ROI)
    position2=[0,0,0]
    ruler.GetPosition2(position2) #Back end of the ruler
    rulerPt=numpy.array(position2)
    closestIndex=0
    for i in range (1,6):
      priorPt=numpy.array(roiPoints[closestIndex])
      nextPt=numpy.array(roiPoints[i])
      #distance functions
      if numpy.linalg.norm(rulerPt-priorPt)>numpy.linalg.norm(rulerPt-nextPt):
        closestIndex=i
    return closestIndex
  def GetOppositeExtent(self,RoiIndex):
    """ A pretty simple function that I only created to improve readibility
    This will just get the ROI extent's opposite point
    In the RAS coordinate System
    RAS 
    L->R  Index [0],[1]
    P->A  Index[2],[3]
    I->S  Index[4],[5]
    
    """
    if RoiIndex%2==0: # Even
      return RoiIndex+1
    else: 
      return RoiIndex-1
  def SortPointsInPlane(self, listOfPoints, vectorPlane):
    """ Sorts points in order based on their distance along the plane in the 
    VectorPlane Direction
    """
    if listOfPoints == []: 
      return []
    else:
      pivot= listOfPoints[0]
      pivotValue = self.DotProduct(pivot,self.catheterVector)
      lesser = self.SortPointsInPlane([x for x in listOfPoints[1:] if
                                 self.utility.DotProduct(x, self.catheterVector) <
                                  pivotValue], self.catheterVector )
      greater= self.SortPointsInPlane([x for x in listOfPoints[1:] if
                                 self.utility.DotProduct(x, self.catheterVector) >=
                                  pivotValue], self.catheterVector)
    return lesser + [pivot] + greater
    
    