# Copyright (c) 2017 Thomas Karl Pietrowski

# TODOs:
# * Adding selection to separately import parts from an assembly

# Build-ins
import math
import os
import winreg
import ctypes

# Uranium/Cura
from UM.i18n import i18nCatalog # @UnresolvedImport
from UM.Message import Message # @UnresolvedImport
from UM.Logger import Logger # @UnresolvedImport
from UM.Math.Matrix import Matrix # @UnresolvedImport
from UM.Math.Vector import Vector # @UnresolvedImport
from UM.Math.Quaternion import Quaternion # @UnresolvedImport
from UM.Mesh.MeshReader import MeshReader # @UnresolvedImport
from UM.PluginRegistry import PluginRegistry # @UnresolvedImport

# Our plugin
from .InventorConstants import ExportUnits, Resolution, OutputFileType
from .CadIntegrationUtils.CommonComReader import CommonCOMReader # @UnresolvedImport
from .CadIntegrationUtils.ComFactory import ComConnector # @UnresolvedImport

i18n_catalog = i18nCatalog("InventorPlugin")


def is_askinv_service():
    service_name =  "Inventor.Application"
    try:
        # Could find a better key to detect whether SolidWorks is installed..
        winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, service_name, 0, winreg.KEY_READ)
        return True
    except:
        return False

class InventorReader(CommonCOMReader):
    def __init__(self):
        super().__init__("Inventor", "Inventor.Application")

        self._extension_part = ".IPT"
        self._extension_assembly = ".IAM"
        self._extension_drawing = ".DWG"
        self._supported_extensions = [self._extension_part.lower(),
                                      self._extension_assembly.lower(),
                                      self._extension_drawing.lower(),
                                      ]



    def setAppVisible(self, state, options):
        options["app_instance"].Visible = state

    def getAppVisible(self, state, options):
        return options["app_instance"].Visible

    def startApp(self, options):
        options = super().startApp(options)

        # Inventor is by default invisible..
        if not options["app_was_active"]:
            options["app_instance_visible"] = options["app_instance"].Visible
            options["app_instance"].Visible = False

        return options

    def closeApp(self, options):
        if "app_instance" in options.keys():
            # Same here. By logic I would assume that we need to undo it, but when processing multiple parts, SolidWorks gets confused again..
            # Or there is another sense..
            if "app_instance_visible" in options.keys():
                options["app_instance"].Visible = options["app_instance_visible"]
            
            if not options["app_was_active"]:
                options["app_instance_visible"] = options["app_instance"].Quit()
    
    
    def getOpenDocuments(self, options):
        open_documents = {}
        if options["app_instance"].Documents.Count:
            for i in range(options["app_instance"].Documents.Count):
                open_document = options["app_instance"].Documents.Item(i+1)
                open_documents[open_document.FullFileName] = open_document
        return open_documents
    
    def getDocumentByPath(self, options, filename):
        if options["app_instance"].Documents.Count:
            for i in range(options["app_instance"].Documents.Count):
                open_document = options["app_instance"].Documents.Item(i+1)
                if open_document.FullFileName == filename:
                    return open_document
        return None
    
    def openForeignFile(self, options):
        document_last_opened = options["app_instance"].ActiveDocument
        if document_last_opened:
            options["document_last_opened"] = document_last_opened
        if options["foreignFile"] not in self.getOpenDocuments(options).keys():
            # http://help.autodesk.com/view/INVNTOR/2018/ENU/?guid=GUID-A1536C12-5AD5-4BA7-9391-2AB32C9B03C7
            options["document"] = options["app_instance"].Documents.Open(options["foreignFile"], False)
            options["document_opened"] = True
        else:
            options["document"] = self.getDocumentByPath(options, options["foreignFile"])
            #if None, then closed in meantime.
            options["document_opened"] = False
        
        if options["foreignFile"].upper().endswith(self._extension_drawing):
            options["parent_document"] = options["document"]
            options["parent_document_opened"] = options["document_opened"]
            
            parts_or_assemblies = []
            for sheet in options["parent_document"].Sheets:
                for drawing_view_i in range(sheet.DrawingViews.Count):
                    drawing_view = sheet.DrawingViews.Item(drawing_view_i+1)
                    item = drawing_view.ReferencedDocumentDescriptor.ReferencedDocument
                    item.FullDocumentName
                    fullfilename = item.FullFileName
                    if fullfilename not in parts_or_assemblies:
                        parts_or_assemblies.append(fullfilename)
            if len(parts_or_assemblies) == 1:
                if parts_or_assemblies[0] not in self.getOpenDocuments(options).keys():
                    # TODO: http://help.autodesk.com/view/INVNTOR/2018/ENU/?guid=GUID-44DDD7C9-D90E-4F49-BEE2-757EE785C826
                    options["document"] = options["app_instance"].Documents.Open(parts_or_assemblies[0], False)
                else:
                    options["document"] = self.getDocumentByPath(options, parts_or_assemblies[0])
        else:
            options["parent_document"] = None

        return options
    
    def optionReplaceValueForKey(self, option, key, value):
        option.Remove(key)
        option.Insert(key, value)

    def exportFileAs(self, options, quality_enum):
        STLTranslatorAddIn = options["app_instance"].ApplicationAddIns.ItemById("{533E9A98-FC3B-11D4-8E7E-0010B541CD80}")
        exportContext = options["app_instance"].TransientObjects.CreateTranslationContext()
        exportOptions = options["app_instance"].TransientObjects.CreateNameValueMap()
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
        if STLTranslatorAddIn.HasSaveCopyAsOptions(options["document"], exportContext, exportOptions):
            # Set Unit
            #options["option_exportunits"] = exportOptions["ExportUnits"] # TODO: Check whether this affects the default settings
            exportOptions.Remove("ExportUnits")
            exportOptions.Insert("ExportUnits", ExportUnits.Millimeter)
            
            # Set accuracy
            # http://help.autodesk.com/view/INVNTOR/2018/ENU/?guid=GUID-5FDFF606-1D15-4FA0-9ED1-1BF4A3BCEBF8
            
            # *** The following are only used for “Custom” resolution
            #  
            # SurfaceDeviation
            #                 0 to 100 for a percentage between values computed based on the size of the model.
            # NormalDeviation
            #                 0 to 40 to indicate values 1 to 41
            # MaxEdgeLength
            #                0 to 100 for a percentage between values computed based on the size of the model.
            # AspectRatio
            #                0 to 40 for values between 1.5 to 21.5 in 0.5 increments
            #
            # https://forums.autodesk.com/t5/inventor-customization/ilogic-stl-translator-specific-parameters-info/td-p/4418665
            
            #options["option_resolution"] = exportOptions["Resolution"] # TODO: Check whether this affects the default settings
            exportOptions.Remove("Resolution")
            exportOptions.Insert("Resolution", Resolution.High)
            
            # Set output file type:
            #options["option_outputfiletype"] = exportOptions["OutputFileType"] # TODO: Check whether this affects the default settings
            exportOptions.Remove("OutputFileType")
            exportOptions.Insert("OutputFileType", OutputFileType.binary)
            
            # Set output file type:
            #options["option_exportcolor"] = exportOptions["ExportColor"] # TODO: Check whether this affects the default settings
            exportOptions.Remove("ExportColor")
            exportOptions.Insert("ExportColor", False)
            
            # IOMechanismEnum Enumerator - http://help.autodesk.com/view/INVNTOR/2018/ENU/?guid=GUID-A3660CD6-8B11-48CE-9FA5-E51DCC6F8DEB
            exportContext.Type = 13059 #kFileBrowseIOMechanism
            
            exportData = options["app_instance"].TransientObjects.CreateDataMedium()
            exportData.FileName = options["tempFile"]
            
            STLTranslatorAddIn.SaveCopyAs(options["document"],
                                          exportContext,
                                          exportOptions,
                                          exportData,
                                          )
        

    def closeForeignFile(self, options):
        
        if "document_opened" in options.keys():
            if options["document"]:
                options["document"].Close(True)
        if "parent_document_opened" in options.keys():
            if options["parent_document"]:
                options["parent_document"].Close(True)
        
        """
        # Needs probably reimplementation
        if options["document_last_opened"]:
            error = ctypes.c_int()
            options["app_instance"].ActivateDoc3(options["sw_previous_active_file"].GetTitle,
                                                 True,
                                                 SolidWorksEnums.swRebuildOnActivation_e.swDontRebuildActiveDoc,
                                                 ctypes.byref(error)
                                                 )
        """
