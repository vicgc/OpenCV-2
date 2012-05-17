import cv2
import numpy as np
import sys
from glob import glob
import math


def dummy(x):
	print x


#Methods for finding up staples in a 3-channel image
def thresholdChannels(img):
	mergeAux=[]
	for channel in cv2.split(img):
		mergeAux.append(cv2.threshold(channel,180,255,cv2.cv.CV_THRESH_BINARY)[1])
	
	aux = cv2.min(mergeAux[0],mergeAux[1])
	aux = cv2.min(aux,mergeAux[2])
	return aux


#Methods for treating the staple contours
def findFrame(contours,dimension,val,sqNum):
	#compute the width and height of a square
	lw = dimension[0]/sqNum
	lh = dimension[1]/sqNum
	sqHist = [] #create an appropiate histogram (2D)
	for i in range(sqNum):
		aux = [0,]*sqNum
		sqHist.append(aux)

	for cont in contours:
		center,r = cv2.minEnclosingCircle(cont)
		x,y = center[0],center[1]
		for i in range(sqNum):
			#if "center is in the vertical frame"  or   the circle intersects the vertical frame
			if(i*lw<x and (i+1)*lw>x)or(abs(x-i*lw)<r or abs(x-(i+1)*lw)<r):
				for j in range(sqNum):
					#if "center is in the horizontal frame" or the circle intersects the horizontal frame
					if(j*lh<y and (j+1)*lh>y)or(abs(y-j*lh)<r or abs(y-(j+1)*lh)<r):
						sqHist[j][i]+=1
	return sqHist


def stapleCont(img,minArea,maxArea,direction):	
	if minArea>maxArea:
		minArea,maxArea=maxArea,minArea

	canvas = np.zeros((img.shape), np.uint8)

	rawContours,hierarchy = cv2.findContours(img.copy(),
		cv2.cv.CV_RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)

	bigCont = [] #contours with more than one element
	for cnt in rawContours:
		if len(cnt)>1:
			cvxH = cv2.convexHull(cnt)
			area = cv2.contourArea(cvxH,False)
			if (area>minArea and area<maxArea):
				bigCont.append(cvxH)
	
	lines =[]
	for points in enumerate(bigCont):
		l = cv2.fitLine(points[1], cv2.cv.CV_DIST_L2, 0, 0.1, 0.1)
		p = (l[2],l[3])
		v = (l[0],l[1])
		lines.append((points[0],v,p))
		
	directionHist = [0,]*4	
	d0,d1,d2,d3 = [],[],[],[]
	contByDirection = [d0,d1,d2,d3]

	for vect in lines:		
		index = vect[0]
		v = vect[1]
		p = vect[2]
		if math.degrees(math.asin(abs(v[1])))<45:
			if ((v[0]>0 and v[1]<=0) or (v[0]<0 and v[1]>=0)) :
				directionHist[0]+=1
				contByDirection[0].append(bigCont[vect[0]])
				if direction==0 or direction==4:
					p2 = (p[0]+10*v[0],p[1]+10*v[1])
					cv2.line(canvas,p,p2,(0,0,255),2)	
			else:
				directionHist[3]+=1
				contByDirection[3].append(bigCont[vect[0]])
				if direction==3 or direction==4:
					p2 = (p[0]+10*v[0],p[1]+10*v[1])
					cv2.line(canvas,p,p2,(0,0,255),2)
		else:
			if ((v[0]>=0 and v[1]<0) or (v[0]<=0 and v[1]>0)) :
				directionHist[1]+=1
				contByDirection[1].append(bigCont[vect[0]])
				if direction==1 or direction==4:
					p2 = (p[0]+10*v[0],p[1]+10*v[1])
					cv2.line(canvas,p,p2,(0,0,255),2)
			else:
				directionHist[2]+=1
				contByDirection[2].append(bigCont[vect[0]])
				if direction==2 or direction==4:
					p2 = (p[0]+10*v[0],p[1]+10*v[1])
					cv2.line(canvas,p,p2,(0,0,255),2)
	if direction == 5:
		cv2.drawContours(canvas,
			contByDirection[directionHist.index(max(directionHist))],
			-1, (255,255,255))
	else:
		cv2.drawContours(canvas, bigCont, -1, (255,255,255))
	return canvas,bigCont

def paintSQS(sqHist,dimension,val):
	canvas = np.zeros((dimension[1],dimension[0]),np.uint8)
	lw = dimension[0]/len(sqHist[0])
	lh = dimension[1]/len(sqHist)
	#paint the result
	for row in enumerate(sqHist):
		for col in enumerate(row[1]):
			if col[1]!=0:
				plane = np.ones((lh,lw),np.uint8)*val
				canvas[row[0]*lh:(row[0]+1)*lh,col[0]*lw:(col[0]+1)*lw]=plane	
	return canvas


def isConnected(row,col,matrix):
	leftB = max(0,col-1)
	rightB = min(col+1,len(matrix[0])-1)
	upB = max(0,row-1)
	downB = min(row+1,len(matrix)-1)
	for i in range(upB,downB+1,1):
		for j in range(leftB,rightB+1,1):
			if (i!=row or j!=col) and (matrix[i][j]!=0):
				return True
	return False


def removeNotConnected(sigSquares):
	for row in enumerate(sigSquares):
		for col in enumerate(row[1]):
			if (sigSquares[row[0]][col[0]]!=0) and (not isConnected(row[0],col[0],sigSquares)):
				sigSquares[row[0]][col[0]]=0


def significantSQS(img,bigCont):
	sigSquares = findFrame(bigCont,(img.shape[1],img.shape[0]),255,5)
	removeNotConnected(sigSquares)
	mask = paintSQS(sigSquares,(img.shape[1],img.shape[0]),120)
	return mask

def doAndPack(img,minArea,maxArea,direction):
	h, w = 375,450
	threshChan = thresholdChannels(img)
	contours,bigCont = stapleCont(threshChan,minArea,maxArea,direction)
	greenMask = significantSQS(contours,bigCont)

	background = np.zeros((h,w*3,3),np.uint8)
	background[0:h,0:w,0:3]=cv2.resize(img,(w,h))
	background[0:h,w:2*w,0:3]=cv2.resize(cv2.merge([threshChan]*3),(w,h))
	background[0:h,2*w:3*w,0:3]=cv2.resize(cv2.merge([contours,greenMask,contours]),(w,h))
	return background


if __name__ == "__main__":
	print 'this script finds all the contours of a'
	print 'specified area and orientation and marks'
	print 'in green the tiles where the contours are found'
	print 'not connected tiles are blended'
	print ''
	print 'use z and x to move through the images'

	path = '../images/*.jpg'
	imageNames = glob(path)
	imgIndex = 0
	img = cv2.imread(imageNames[imgIndex])	
	
	cv2.namedWindow('panel',cv2.cv.CV_WINDOW_NORMAL)
	cv2.createTrackbar('minArea','panel',0,500,dummy)
	cv2.createTrackbar('maxArea','panel',5000,5000,dummy)
	cv2.createTrackbar('direction','panel',0,5,dummy)

	bigImg = doAndPack(img,
		cv2.getTrackbarPos('minArea','panel'),
		cv2.getTrackbarPos('maxArea','panel'),
		cv2.getTrackbarPos('direction','panel'))

	while True:
		bigImg = doAndPack(img,
			cv2.getTrackbarPos('minArea','panel'),
			cv2.getTrackbarPos('maxArea','panel'),
			cv2.getTrackbarPos('direction','panel'))

		cv2.imshow('original',bigImg)

		key = cv2.waitKey(5)
	 	if (key==120):
	 		imgIndex = (imgIndex+1,imgIndex)[imgIndex==(len(imageNames)-1)]
	 		img = cv2.imread(imageNames[imgIndex])
	 	elif (key==122):
	 		imgIndex = (imgIndex-1,imgIndex)[imgIndex==0]
	 		img = cv2.imread(imageNames[imgIndex])

	 	elif (key != -1):
	 		break



	
