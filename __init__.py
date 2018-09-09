# Copyright (c) 2017 Thomas Karl Pietrowski

# built-ins
import os

# Uranium
from UM.Message import Message # @UnresolvedImport
from UM.Platform import Platform # @UnresolvedImport
from UM.i18n import i18nCatalog # @UnresolvedImport

i18n_catalog = i18nCatalog("InventorPlugin")

if Platform.isWindows():
    # For installation check
    import winreg
    # The reader plugin itself
    from . import InventorReader

def getMetaData():
    metaData = {"mesh_reader": [{
                                 "extension": "IPT",
                                 "description": i18n_catalog.i18nc("@item:inlistbox", "Autodesk Inventor part file")
                                 },
                                {
                                 "extension": "IAM",
                                 "description": i18n_catalog.i18nc("@item:inlistbox", "Autodesk Inventor assembly file")
                                 },
                                {
                                 "extension": "DWG",
                                 "description": i18n_catalog.i18nc("@item:inlistbox", "Autodesk Inventor drawing file")
                                 },
                                ],
                }

    return metaData

def register(app):
    # Autodesk Inventor only runs on Windows.
    plugin_data = {}
    if Platform.isWindows():
        reader = InventorReader.InventorReader()
        if InventorReader.is_askinv_service():
            # TODO: Add error message about not found INV installation
            plugin_data["mesh_reader"] = reader
        else:
            no_valid_installation_message = Message(i18n_catalog.i18nc("@info:status",
                                                                       "Dear customer,\nWe could not find a valid installation of Autodesk Inventor on your system. That means that either Autodesk Inventor is not installed or you don't own an valid license. Please make sure that running Autodesk Inventor itself works without issues and/or contact your ICT.\n\nWith kind regards\n - Thomas Karl Pietrowski"
                                                                       ),
                                                    0)
            no_valid_installation_message.setTitle("Autodesk Inventor plugin")
            no_valid_installation_message.show()
    else:
        not_correct_os_message = Message(i18n_catalog.i18nc("@info:status",
                                                            "Dear customer,\nYou are currently running this plugin on an operating system other than Windows. This plugin will only work on Windows with Autodesk Inventor installed, including an valid license. Please install this plugin on a Windows machine with Autodesk Inventor installed.\n\nWith kind regards\n - Thomas Karl Pietrowski"
                                                            ),
                                         0)
        not_correct_os_message.setTitle("Autodesk Inventor plugin")
        not_correct_os_message.show()
    return plugin_data
