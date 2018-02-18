# -*- coding: utf-8 -*-

'''
Created on 07.11.2017

@author: Thomas Pietrowski
@api: http://help.autodesk.com/view/INVNTOR/2018/ENU/?guid=GUID-AA811AF0-2494-4574-8C43-4C22E608252F
'''

import os

import ctypes

import win32com
win32com.__gen_path__ = os.path.join(os.path.split(__file__)[0], "gen_dir") 

import win32com.client
import pythoncom

def getOpenDocuments():
    open_documents = {}
    if ThisApplication.Documents.Count:
        for i in range(ThisApplication.Documents.Count):
            open_document = ThisApplication.Documents.Item(i+1)
            open_documents[open_document.FullFileName] = open_document
    return open_documents

def getDocumentByPath(filename):
    if ThisApplication.Documents.Count:
        for i in range(ThisApplication.Documents.Count):
            open_document = ThisApplication.Documents.Item(i+1)
            if open_document.FullFileName == filename:
                return open_document
    return None


#ThisApplication = win32com.client.gencache.EnsureDispatch("Inventor.Application")
try:
    ThisApplication = win32com.client.GetActiveObject("Inventor.Application")
except:
    ThisApplication = win32com.client.Dispatch("Inventor.Application")
    #ThisApplication.Visible=True

#foreign_filename = ".\\tests\\Inventor Professional 2018\\test_cube.ipt"
#foreign_filename = ".\\test\\Inventor Professional 2018\\test_cube.iam"
foreign_filename = ".\\tests\\Inventor Professional 2018\\test_cube.dwg"
foreign_filename = os.path.realpath(foreign_filename)

#Document = ThisApplication.ActiveDocument

if foreign_filename not in getOpenDocuments().keys():
    # http://help.autodesk.com/view/INVNTOR/2018/ENU/?guid=GUID-A1536C12-5AD5-4BA7-9391-2AB32C9B03C7
    document = ThisApplication.Documents.Open(foreign_filename, False)
    document_opened = True
else:
    document = document = getDocumentByPath(foreign_filename)
    document_opened = False

if foreign_filename.endswith(".dwg"):
    parent_document = document
    parent_document_opened = document_opened
    
    parts_or_assemblies = []
    for sheet in parent_document.Sheets:
        for drawing_view_i in range(sheet.DrawingViews.Count):
            drawing_view = sheet.DrawingViews.Item(drawing_view_i+1)
            item = drawing_view.ReferencedDocumentDescriptor.ReferencedDocument
            item.FullDocumentName
            fullfilename = item.FullFileName
            if fullfilename not in parts_or_assemblies:
                parts_or_assemblies.append(fullfilename)
    print(parts_or_assemblies)
    if len(parts_or_assemblies) == 1:
        if parts_or_assemblies[0] not in getOpenDocuments().keys():
            document = ThisApplication.Documents.Open(parts_or_assemblies[0], False)
        else:
            document = getDocumentByPath(parts_or_assemblies[0])
else:
    parent_document = None 

STLTranslatorAddIn = ThisApplication.ApplicationAddIns.ItemById("{533E9A98-FC3B-11D4-8E7E-0010B541CD80}")
Context = ThisApplication.TransientObjects.CreateTranslationContext()
Options = ThisApplication.TransientObjects.CreateNameValueMap()
#    Save Copy As Options:
#       Name Value Map:
#               ExportUnits = 4
#               Resolution = 1
#               AllowMoveMeshNode = False
#               SurfaceDeviation = 60
#               NormalDeviation = 14
#               MaxEdgeLength = 100
#               AspectRatio = 40
#               ExportFileStructure = 0
#               OutputFileType = 0
#               ExportColor = True

if STLTranslatorAddIn.HasSaveCopyAsOptions(document, Context, Options):
    # Set accuracy.
    #   2 = High,  1 = Medium,  0 = Low
    # was 4
    
    # http://help.autodesk.com/view/INVNTOR/2018/ENU/?guid=GUID-5FDFF606-1D15-4FA0-9ED1-1BF4A3BCEBF8
    Options.Remove("Resolution")
    Options.Insert("Resolution", 2)
    
    # Set output file type:
    #   0 - binary,  1 - ASCII
    Options.Remove("OutputFileType")
    Options.Insert("OutputFileType", 1)

    # IOMechanismEnum Enumerator - http://help.autodesk.com/view/INVNTOR/2018/ENU/?guid=GUID-A3660CD6-8B11-48CE-9FA5-E51DCC6F8DEB
    Context.Type = 13059 #kFileBrowseIOMechanism

    Data = ThisApplication.TransientObjects.CreateDataMedium()
    filedir, filename = os.path.split(foreign_filename)
    # if "." in filename
    real_filename = os.path.splitext(filename)[0]
    stl_filename = real_filename + ".stl"
    stl_fullpath = os.path.join(filedir, stl_filename)
    Data.FileName = stl_fullpath
    print("saved as: {}".format(stl_fullpath))

    STLTranslatorAddIn.SaveCopyAs(document, Context, Options, Data)

if document_opened:
    document.Close(True)
if parent_document_opened:
    parent_document.Close(True)