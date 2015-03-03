class TestObject:
  def SetGlobalParameters(self,ROI,normal,distanceBetweenTubes,maskThickness):
    """Only Set These Once"""
    self.utility=Util_HDR()
    self.distanceBetweenTubes=distanceBetweenTubes
    self.maskThickness=maskThickness
    self.ROIExtents=ROI
    self.normal=normal
    self.bottomPlane=self.CreateBottomPlane()
    self.PATH= ROOTPATH+"\\doc\\DebugPolyData\\"
    self.TUBENUMBER=0
    self.tubeList=[]
    self.planeList=[]
    self.combinedTubePlane=[]
    self.tubes=[]
    self.currentY=0
  def SetLocalParameters(self,minimumCurvature,tubeRadius,planeWidth):
    self.tubeRadius=tubeRadius
    self.lengthPath=70
    self.startPoint=[0,self.currentY,0]
    self.currentY+=(self.tubeRadius)+self.distanceBetweenTubes+2
    self.minimumCurvature=minimumCurvature
    self.planeWidth=planeWidth
    #self.circleInfo=(center1,center2,center3)
    self.circleInfo=self.CreateCircles(self.startPoint, self.minimumCurvature)
    self.path=self.CreatePath()
    self.planeList.append(self.OpeningPlane())
    self.tubes.append(self.CreateTubes())


  def __init__(self):
    """ROI, Normal, Distance between tubes mm ,maskthickness"""
    self.SetGlobalParameters([0,70,-5,50,-5,50],(0,0,1),8,3)
    
    """(self.minimumCurvature, self.tubeRadius, planeWidth)"""
    #Catheter Radius = 1.0
    self.SetLocalParameters(10, 1.0, 1.0)
    self.SetLocalParameters(12, 1.0, 1.0)
    self.SetLocalParameters(14, 1.0, 1.0)
    self.SetLocalParameters(16, 1.0, 1.0)
    
    #Catheter Radius = 1.25
    self.SetLocalParameters(10, 1.333, 1.0)
    self.SetLocalParameters(12, 1.333, 1.0)
    self.SetLocalParameters(14, 1.333, 1.0) # Winner
    self.SetLocalParameters(16, 1.333, 1.0)
     
    #Catheter Radius = 1.5
    self.SetLocalParameters(10, 1.667, 1.5)
    self.SetLocalParameters(12, 1.667, 1.5)
    self.SetLocalParameters(14, 1.667, 1.5)
    self.SetLocalParameters(16, 1.667, 1.5)
    
    appendedPolydata=vtk.vtkAppendPolyData()
    i=0
    for item in self.tubes:
      i+=1
      appendedPolydata.AddInputConnection(item.GetOutputPort())
      #self.utility.DisplayPolyData("tube"+str(i), item.GetOutput())
    self.utility.DisplayPolyData("wholeMask", appendedPolydata.GetOutput())
    
#     boxFunction=vtk.vtkBox()
#     boxFunction.SetBounds([-10,70,-10,50,-100,100])
#     clippingFilter=vtk.vtkCutter()
#     clippingFilter.SetInputConnection(appendedPolydata.GetOutputPort())
#     clippingFilter.SetCutFunction(boxFunction)
#     clippingFilter.SetValue(0,0)
#     self.utility.DisplayPolyData("clippedWholeMask", clippingFilter.GetOutput())
    
    return
  def ExtendPath(self):
    numberOfPoints=self.path.GetNumberOfPoints()+2
    points=self.path.GetPoints()
    newPoints=vtk.vtkPoints()
    newPoints.SetNumberOfPoints(numberOfPoints)
    newPoints.SetPoint(0,-10,self.circleInfo[0][1],0)
    for i in range (self.path.GetNumberOfPoints()):
      newPoints.SetPoint(i+1,points.GetPoint(i))
    newPoints.SetPoint(numberOfPoints-1,self.lengthPath+5,self.circleInfo[0][1],0)
    
    cellArray=vtk.vtkCellArray() #CellArray used in PolyData
    aLine = vtk.vtkIdList() 
    aLine.SetNumberOfIds(numberOfPoints)
    for i in range (numberOfPoints):
      aLine.SetId(i, i)
    cellArray.InsertNextCell(aLine)
    newPd=vtk.vtkPolyData()
    newPd.SetPoints(newPoints)
    newPd.SetLines(cellArray)
    
    spline = vtk.vtkKochanekSpline()
    splineFilter = vtk.vtkSplineFilter()
    splineFilter.SetInputData(newPd)
    splineFilter.SetSubdivideToLength()
    NUMBER_OF_MM_BETWEEN_POINTS=1
    splineFilter.SetLength(NUMBER_OF_MM_BETWEEN_POINTS)
    splineFilter.SetSpline(spline)
    splineFilter.Update()
    return splineFilter.GetOutput()
  def CreateTubes(self):
    """Creates the tubes that hold the catheters."""
    
    extendedPath=self.ExtendPath()
    cathNormals=vtk.vtkPolyDataNormals()
    cathNormals.SetInputData(extendedPath)
    cathNormals.AutoOrientNormalsOn()
    catheterHole=vtk.vtkTubeFilter()
    catheterHole.CappingOn()
    catheterHole.SetInputData(cathNormals.GetOutput())
    catheterHole.SetNumberOfSides(100)
    catheterHole.SetRadius(self.tubeRadius)
    cathNormals=vtk.vtkPolyDataNormals()
    cathNormals.FlipNormalsOn()
    cathNormals.SetInputConnection(catheterHole.GetOutputPort())
    self.utility.DisplayPolyData("cathNormals", cathNormals.GetOutput())
    
    tube=vtk.vtkTubeFilter()
    tube.CappingOn()
    tube.SetInputData(self.path)
    tube.SetNumberOfSides(100)
    tube.SetRadius(self.distanceBetweenTubes)
    tube.UseDefaultNormalOn()
    tubeNormals=vtk.vtkPolyDataNormals()
    tubeNormals.SetInputConnection(tube.GetOutputPort())
    self.utility.DisplayPolyData("tubeNormals", tubeNormals.GetOutput())
    
    HEIGHT=50
    cube = vtk.vtkCubeSource()
    cube.SetXLength(self.lengthPath+20)
    cube.SetYLength(self.planeWidth)
    cube.SetZLength(HEIGHT)
    cube.SetCenter(self.lengthPath/2,self.circleInfo[0][1],0+HEIGHT/2)
    cutTriangles=vtk.vtkTriangleFilter()
    cutTriangles.SetInputConnection(cube.GetOutputPort())
    cubeNormals=vtk.vtkPolyDataNormals()
    cubeNormals.AutoOrientNormalsOn()
    cubeNormals.SetInputConnection(cutTriangles.GetOutputPort())
    cubeTubeDifference=vtk.vtkBooleanOperationPolyDataFilter()
    cubeTubeDifference.SetOperationToDifference()
    cubeTubeDifference.SetInputConnection(0,tubeNormals.GetOutputPort())
    cubeTubeDifference.SetInputConnection(1,cubeNormals.GetOutputPort())
    self.utility.DisplayPolyData("Removed", cubeTubeDifference.GetOutput())
    
    cathAndCutTubeDiff=vtk.vtkBooleanOperationPolyDataFilter()
    cathAndCutTubeDiff.SetOperationToIntersection()
    cathAndCutTubeDiff.SetInputConnection(0,cubeTubeDifference.GetOutputPort())
    cathAndCutTubeDiff.SetInputConnection(1,cathNormals.GetOutputPort())
    #self.utility.DisplayPolyData("Second", cathAndCutTubeDiff.GetOutput())
    return cathAndCutTubeDiff
  def ShiftPathUp(self,path,mmAmount):
    points=path.GetPoints()
    newPoints=vtk.vtkPoints()
    newPoints.SetNumberOfPoints(points.GetNumberOfPoints())
    for i in range (path.GetNumberOfPoints()):
      newPoints.SetPoint(i,points.GetPoint(i)[0],points.GetPoint(i)[1],points.GetPoint(i)[2]+mmAmount)
    cellArray=vtk.vtkCellArray() #CellArray used in PolyData
    aLine = vtk.vtkIdList() 
    aLine.SetNumberOfIds(points.GetNumberOfPoints())
    for i in range (points.GetNumberOfPoints()):
      aLine.SetId(i, i)
    cellArray.InsertNextCell(aLine)
    newPd=vtk.vtkPolyData()
    newPd.SetPoints(newPoints)
    newPd.SetLines(cellArray)
    return newPd
  def GenerateFinalMask(self):
    unionOfTubes=vtk.vtkBooleanOperationPolyDataFilter()
    unionOfTubes.SetOperationToUnion()
    i=0
    for item in self.tubes:
      unionOfTubes.SetInputConnection(i,item.GetOutputPort())
      i+=1
    return unionOfTubes.GetOutput()
    
  def Combine(self):
    subtractionFilter1=vtk.vtkBooleanOperationPolyDataFilter()
    subtractionFilter1.SetOperationToDifference()
    subtractionFilter1.SetInputData(self.tubeList[-1])
    subtractionFilter1.SetInputData(self.planeList[-1])
    return subtractionFilter1.GetOutput()
  def OpeningPlane(self):
    cube = vtk.vtkCubeSource()
    cube.SetBounds(self.startPoint[0]+5,self.ROIExtents[1]-5, # L,R
                   self.startPoint[1]-self.planeWidth,self.startPoint[1]+self.planeWidth, #A,P
                   self.startPoint[2]+self.tubeRadius,self.ROIExtents[5]) #I,S
    return cube
  def CreatePath(self, pointsPerQuarterRotation=90):
    pointsPerCircle=pointsPerQuarterRotation*4+1 #EndPoint
    points=vtk.vtkPoints()
    points.SetNumberOfPoints(pointsPerCircle)
    Ycomp=self.circleInfo[0][1] # never changes
    while pointsPerQuarterRotation!=0:
      oppositeSide=self.minimumCurvature*numpy.sin(numpy.radians(90-pointsPerQuarterRotation))
      adjacentSide=self.minimumCurvature*numpy.cos(numpy.radians(90-pointsPerQuarterRotation))
      #First Quarter Rotation
      indexFirstRotation=90-pointsPerQuarterRotation
      indexSecondRotation=indexFirstRotation+90
      indexThirdRotation=indexSecondRotation+90
      indexForthRotation=indexThirdRotation+90
      
      points.InsertPoint(indexFirstRotation,
                         oppositeSide,
                         Ycomp,
                         self.minimumCurvature-adjacentSide)
      
      points.InsertPoint(indexSecondRotation,
                         self.minimumCurvature*2-adjacentSide, 
                         Ycomp,
                         oppositeSide+self.minimumCurvature)
      
      points.InsertPoint(indexThirdRotation,
                         2*self.minimumCurvature+oppositeSide,
                         Ycomp,
                         self.minimumCurvature+adjacentSide)
      
      points.InsertPoint(indexForthRotation,
                         self.minimumCurvature*4-adjacentSide,
                         Ycomp,
                         self.minimumCurvature-oppositeSide)
      pointsPerQuarterRotation-=1
      
    points.InsertPoint(360,self.lengthPath,Ycomp,0)
    cellArray=vtk.vtkCellArray() #CellArray used in PolyData
    aLine = vtk.vtkIdList() 
    aLine.SetNumberOfIds(361)
    for i in range (361):
      aLine.SetId(i, i)
    cellArray.InsertNextCell(aLine)
    newPolyData=vtk.vtkPolyData()
    newPolyData.SetPoints(points)
    newPolyData.SetLines(cellArray)
    
    
    
    spline = vtk.vtkKochanekSpline()
    splineFilter = vtk.vtkSplineFilter()
    splineFilter.SetInputData(newPolyData)
    splineFilter.SetSubdivideToLength()
    NUMBER_OF_MM_BETWEEN_POINTS=1
    splineFilter.SetLength(NUMBER_OF_MM_BETWEEN_POINTS)
    splineFilter.SetSpline(spline)
    splineFilter.Update()
    return splineFilter.GetOutput()
  def CreateBottomPlane(self):
    implicitPlane= vtk.vtkPlane()
    implicitPlane.SetNormal(self.normal)
    implicitPlane.SetOrigin(0,0,0)
    return implicitPlane
    #self.utility.DisplayImplicit("BottomPlane", self.bottomPlane)
  def CreateCircles(self,startPoint,radius):
    a,b,c=startPoint
    center1=a,b,c+radius # X= Path-lengthwise, Y=between tubes Z=vertically 
    center2=a+2*radius,b,c+radius # for making the circles
    center3=a+4*radius,b,c+radius
    return (center1,center2,center3)