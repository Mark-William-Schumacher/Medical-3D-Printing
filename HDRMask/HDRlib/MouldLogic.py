from Utility import *
from __main__ import vtk


class MouldLogic:
  """ Defines the logic for creating the mould
  """
  def __init__(self, numberOfPaths, DEBUGCONNECTIVEFACE,DEBUGSLITPLANES, PATH):
    self.ROOTPATH = PATH
    self.DEBUG_CONNECTIVITYFACE = DEBUGCONNECTIVEFACE
    self.DEBUG_SLITPLANES = DEBUGSLITPLANES
    self.count=0 #used for creating unique names in debug
    self.numberOfPaths=numberOfPaths.currentNode().GetNumberOfFiducials() 
    self.utility=Util_HDR() #utility Object with common methods
    self.skinSurface=None # Set after ClipData()
    self.minimumDistanceMask= None # Set after MinimumDistanceMask()
    self.clippedSurface= None # Set after ClipData()
    self.listOfCatheters=[] # Set After CreateRawPath()
    self.listOfPlanes=[] #Implicit Planes , created after CreatePlane()
    self.listOfBackLines=[] # The line created at the back of the Mask
    self.listOfNormals=[]
    self.slitPlanes=[]
    self.tubes=[]
    self.channels= [] #The Channels are the plastic surronding the empty tubes 
  def ClipData(self, ROI , noisySurfacePolyData):
    """ Returns the clipped polydata from the region defined by the ROI
    Turn on the Debug to make the clipped object appear, 
    For specific filter functionality see DataFlow doc: ClipData.pdf
    """
    connectivityFilter = vtk.vtkPolyDataConnectivityFilter()
    self.utility.PolyDataWriter(noisySurfacePolyData,
                                "C:\\MakeHDRApplicatorMask\\doc\\"+\
                                "DebugPolyData\\PreClipped.vtk")
    connectivityFilter.SetInputData(noisySurfacePolyData)
    connectivityFilter.SetExtractionModeToLargestRegion()
    connectivityFilter.Update()
    self.skinSurface=connectivityFilter.GetOutput()  #skinSurface Set
    if self.DEBUG_CONNECTIVITYFACE:
      self.utility.DisplayPolyData("ConnectedFace", self.skinSurface)
    # Expansion of ROI is explained in vtkImplicitModeller limitations
    ROIExtents= self.utility.GetROIExtents(ROI)
    BiggerROI=self.utility.ExpandExtents(ROIExtents, .5)
    #See vtkImplicitModdeler limitations.pdf for explanation
    implicitBoxRegion = vtk.vtkBox()
    implicitBoxRegion.SetBounds(BiggerROI)
    
    clipper=vtk.vtkClipPolyData()
    clipper.InsideOutOn() # Clip the regions outside of implicit function
    clipper.SetInputConnection(connectivityFilter.GetOutputPort())
    clipper.SetClipFunction(implicitBoxRegion)
    clipper.Update()
    self.clippedSurface=clipper.GetOutput()
    return clipper
  def CreateMultiplePlanes(self,startPoints,endPoints,ruler):
    """ Gets the inputs ready for input into createPlane()
    this function will return back multiple implicit planes in one list
    """
    rulerDirection=self.utility.GetRulerVector(ruler) 
    for i in range(len(startPoints)):   #create num of planes for each pair
      startPoint = startPoints[i]
      endPoint = endPoints[i]
      self.CreatePlane(startPoint,endPoint,rulerDirection)
  def CreatePlane(self, startPoint, endPoint, direction):
    """ Takes two points and a direction vector
    returns an implicit function defining a plane
    """
    a,b,c=startPoint #quick unpack
    d,e,f=endPoint #quick unpack
    q,r,s=a-d,b-e,c-f #quick direction vector
    catheterDirection=[q,r,s]
    normal = self.utility.CrossProduct(direction, catheterDirection)
    self.listOfNormals.append(normal)
    implicitPlane= vtk.vtkPlane()
    implicitPlane.SetNormal(normal)
    implicitPlane.SetOrigin(startPoint)
    self.listOfPlanes.append(implicitPlane) # Saving plane objects onto object
  def DisplayPlanes(self,listOfPlanes,ROI):
    """ This function is preparation before sending into the more
    general function DisplayImplicit()
    Note, any changing of the color of display of the planes is 
    done so here. 
    """
    for index in range(len(listOfPlanes)):
      name="Plane-"+str(self.count) #To Create Unique Name Required
      self.count+=1 # Increment the unique name for the plane
      node=self.utility.DisplayImplicit(name, listOfPlanes[index],ROI)
      node.SetColor(1,0,0) #Red ...Max 1 for each column
      node.SetOpacity(0.4)
      

  def MinimumDistanceMask(self, vtkAlgorythmObject, distanceFromMask, ROI, ruler , isBubble = False):
    """ Takes an algorythm object which is will send through a pipeline to 
    create a mask defining the minimum distance value from the skin surface
    returns an algorythm object as well to preform GetOutput() -> polydata
    or GetOutputPort() -> algorythm
    see MinimumDistanceMask.pdf 
    """
    if distanceFromMask<2:
      print "WARNING: MouldLogic: MinimumDistanceMask implicit",
      "modeling is very unstable below 1.5 , mask may degrade",
      "and lines will become discontinuous."
    Extents=self.utility.GetROIExtents(ROI)
    if (isBubble):
      Extents=self.utility.ExpandExtents(Extents, 100)
    implicitModeller = vtk.vtkImplicitModeller()
    implicitModeller.SetInputConnection(vtkAlgorythmObject.GetOutputPort())
    implicitModeller.SetMaximumDistance(distanceFromMask)
    implicitModeller.SetModelBounds(Extents)
    implicitModeller.AdjustBoundsOn()
    implicitModeller.SetAdjustBounds(10) # Removes the boundary effects
    implicitModeller.CappingOff()# Important to create disjoint inner and outer masks
    implicitModeller.SetProcessModeToPerVoxel()
    implicitModeller.Update()
    
    contourFilter = vtk.vtkContourFilter()
    contourFilter.SetValue(0, distanceFromMask)
    contourFilter.SetInputConnection(implicitModeller.GetOutputPort())
    contourFilter.Update()  
    
    normalsFunction = vtk.vtkPolyDataNormals()
    normalsFunction.FlipNormalsOn ()
    normalsFunction.AddInputConnection(contourFilter.GetOutputPort())
    normalsFunction.Update()
    
    implicitBoxRegion = vtk.vtkBox()
    implicitBoxRegion.SetBounds(Extents)
    clipper2=vtk.vtkClipPolyData()
    clipper2.InsideOutOn() # Clip the regions outside of implicit function
    clipper2.SetInputConnection(normalsFunction.GetOutputPort())
    clipper2.SetClipFunction(implicitBoxRegion)
    clipper2.Update()
    
    closestPoint=[0,0,0]
    ruler.GetPosition1(closestPoint)
    connectivityFilter = vtk.vtkPolyDataConnectivityFilter()
    connectivityFilter.SetInputConnection(clipper2.GetOutputPort())
    connectivityFilter.SetExtractionModeToClosestPointRegion()
    connectivityFilter.SetClosestPoint(closestPoint)
    connectivityFilter.Update()
    
    return connectivityFilter.GetOutput()
  def CreateBackLine(self,ruler,ROI,implicitPlane):
    """ Creates the polydata for where the cutting plane hits the the back
    of the ROI.  
    This backline will be used to close the catheter path allowing for the
    specification of Towards or Away from the face
    
    ASSERTION: that the ruler's second point will be closest to the 
    front of our mask. 
    """
    roiPoints=self.utility.GetROIPoints(ROI)
    frontExtentIndex=self.utility.GetClosestExtent(ruler,ROI)
    backExtentIndex=self.utility.GetOppositeExtent(frontExtentIndex)
    
    #Creating an implict plane for the back of the ROI
    ROICenterPoint = [0,0,0]
    ROI.GetXYZ(ROICenterPoint)
    backNormal=self.utility.GetVector(ROICenterPoint, roiPoints[backExtentIndex])
    backPlane= vtk.vtkPlane()
    backPlane.SetNormal(backNormal)
    backPlane.SetOrigin(roiPoints[backExtentIndex])
    
    #Finding the Intercept of this and the CuttingPlane
    sampleFunction=vtk.vtkSampleFunction()
    sampleFunction.SetSampleDimensions(10,10,10)
    sampleFunction.SetImplicitFunction(backPlane)
    bounds=self.utility.ExpandExtents(self.utility.GetROIExtents(ROI),1)
    sampleFunction.SetModelBounds(bounds)
    sampleFunction.Update()
    
    contourFilter=vtk.vtkContourFilter()
    contourFilter.SetInputConnection(sampleFunction.GetOutputPort())
    contourFilter.GenerateValues(1,1,1)
    contourFilter.Update()
    
    cutter=vtk.vtkCutter()
    cutter.SetInputConnection(contourFilter.GetOutputPort())
    cutter.SetCutFunction(implicitPlane)
    cutter.GenerateValues(1,1,1)
    cutter.Update()
    self.listOfBackLines.append(cutter.GetOutput())
    PATH= self.ROOTPATH+"\\doc\\DebugPolyData\\"+"BackLine-"+str(len(self.listOfBackLines))
    self.utility.PolyDataWriter(self.listOfBackLines[-1],PATH+".vtk")
  def AddTubeToMask(self,maskPolydata,tube,ROI,radius,ruler):
    ROIExtents=self.utility.GetROIExtents(ROI)
    implicitFilter = vtk.vtkImplicitModeller()
    implicitFilter.SetInput(tube)
    implicitFilter.SetSampleDimensions(70,70,70)
    implicitFilter.SetMaximumDistance(radius)
    implicitFilter.SetModelBounds(ROIExtents)
    implicitFilter.SetProcessModeToPerVoxel()
    contourFilter = vtk.vtkContourFilter()
    contourFilter.SetValue(0, radius)
    implicitFilter.AdjustBoundsOn()
    implicitFilter.SetAdjustBounds(1) # Removes the boundary effects
    implicitFilter.CappingOff()
    contourFilter.SetInputConnection(implicitFilter.GetOutputPort())
    normalsFunction = vtk.vtkPolyDataNormals()
    normalsFunction.AutoOrientNormalsOn()
    normalsFunction.AddInputConnection(contourFilter.GetOutputPort())
    
    unionFilter = vtk.vtkBooleanOperationPolyDataFilter()
    unionFilter.SetOperationToUnion()
    unionFilter.SetInput(0, normalsFunction.GetOutput())
    unionFilter.SetInput(1, maskPolydata)
    return unionFilter.GetOutput()
  def GenerateMould(self,facePolydata,distanceFromMask,ROI,tubePolydata,clippedFace):
    ROIExtents=self.utility.GetROIExtents(ROI)
    outerFaceImplicitFunction = vtk.vtkImplicitModeller()
    outerFaceImplicitFunction.SetInputConnection(facePolydata.GetOutputPort())
    outerFaceImplicitFunction.SetSampleDimensions(70,70,70)
    outerFaceImplicitFunction.SetMaximumDistance(distanceFromMask)
    outerFaceImplicitFunction.SetModelBounds(ROIExtents)
    outerFaceImplicitFunction.SetProcessModeToPerVoxel()
    outerMaskContourFunction = vtk.vtkContourFilter()
    #TODO Find out the the allowed thinkness of the plastic
    THICKNESS=3
    outerMaskContourFunction.SetValue(0, THICKNESS)
    outerMaskContourFunction.SetInputConnection(outerFaceImplicitFunction.GetOutputPort())  
    
    outerFaceNormalsFunction = vtk.vtkPolyDataNormals()
    outerFaceNormalsFunction.AutoOrientNormalsOn()
    outerFaceNormalsFunction.AddInputConnection(outerMaskContourFunction.GetOutputPort())
    # Subtract the Tubes from the mask 
    subtractionFilter1 = vtk.vtkBooleanOperationPolyDataFilter()
    subtractionFilter1.SetOperationToDifference()
    subtractionFilter1.SetInputConnection(0, outerFaceNormalsFunction.GetOutputPort())
    subtractionFilter1.SetInputConnection(1, tubePolydata.GetOutputPort())
    # Subtract the inner face from the outer face to make the mask
    subtractionFilter2 = vtk.vtkBooleanOperationPolyDataFilter()
    subtractionFilter2.SetOperationToDifference()
    subtractionFilter2.SetInputConnection(0, subtractionFilter1.GetOutputPort())
    subtractionFilter2.SetInputConnection(1, clippedFace.GetOutputPort())
    x=self.utility.DisplayPolyData("Mask", subtractionFilter2.GetOutput())
    x.SetColor(0.8,0.8,0.8)
    x.SetOpacity(1)
  def CreateSlit(self,normal,pathPolydata,ruler,ROI,slitSize):
    """ Here we are going to create a boxSource , the size of the 2*ROI in the X,Y
    and the size of the slit Size in the Z. 
    We are then going to translate the box source to its correct location in slicer
    As always to visualize , a DEBUG option can be set at the top.
    x is L->R, y is P->A, z is I->S
    """ 
    #Cube Creation
    roiPoints=self.utility.GetROIPoints(ROI)
    frontExtentIndex=self.utility.GetClosestExtent(ruler,ROI)
    backExtentIndex=self.utility.GetOppositeExtent(frontExtentIndex)
    pointA=numpy.array(roiPoints[frontExtentIndex])
    pointB=numpy.array(roiPoints[backExtentIndex])
    yDist = numpy.linalg.norm(pointA-pointB)
    numPoints=pathPolydata.GetNumberOfPoints()
    pointA=numpy.array(pathPolydata.GetPoint(0))
    pointB=numpy.array(pathPolydata.GetPoint(numPoints-1))
    xDist = numpy.linalg.norm(pointA-pointB)
    zDist=slitSize #Rewording the parameter to make it easier to understand
    slitCube=vtk.vtkCubeSource()
    slitCube.SetBounds(0,xDist,-yDist,yDist,-zDist/2,zDist/2)# (Xmin, Xmax, Ymin, Ymax,Zmin, Zmax)
    
    #Transforming Cube
    transformFilter=vtk.vtkTransformFilter()
    transform=vtk.vtkTransform()
    matrix=vtk.vtkMatrix4x4()
    pointA=numpy.array(pathPolydata.GetPoint(0))
    pointB=numpy.array(pathPolydata.GetPoint(numPoints-1))
    xVector=pointA-pointB
    xDist = numpy.linalg.norm(pointA-pointB)
    xUnitVector=(xVector[0]/xDist,xVector[1]/xDist,xVector[2]/xDist)
    
    yVector=self.utility.GetRulerVector(ruler)
    yDist=numpy.linalg.norm(yVector)
    yUnitVector=(yVector[0]/yDist,yVector[1]/yDist,yVector[2]/yDist)
    
    zVector=numpy.cross(xVector,yVector)
    zDist=numpy.linalg.norm(zVector)
    zUnitVector= (zVector[0]/zDist,zVector[1]/zDist,zVector[2]/zDist)
    
    origin=pointA=numpy.array(pathPolydata.GetPoint(numPoints-1))
    
    matrix.DeepCopy((xUnitVector[0], yUnitVector[0], zUnitVector[0], origin[0],
                     xUnitVector[1], yUnitVector[1], zUnitVector[1], origin[1],
                     xUnitVector[2], yUnitVector[2], zUnitVector[2], origin[2],
                     0, 0, 0, 1))
    
    transform.SetMatrix(matrix)
    transformFilter.SetTransform(transform)
    transformFilter.SetInputConnection(slitCube.GetOutputPort())
    transformFilter.Update()
    self.slitPlanes.append(transformFilter.GetOutput())
    if len(self.slitPlanes)==self.numberOfPaths and self.DEBUG_SLITPLANES==True:
      for i in range (self.numberOfPaths):
        self.utility.DisplayPolyData("Slit"+str(i), self.slitPlanes[i])
    return transformFilter.GetOutput()
