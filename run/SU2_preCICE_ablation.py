#!/usr/bin/env python3

## File edited to work coupled with preCICE - Joseph Signorelli

## \file flatPlate_rigidMotion.py
#  \brief Python script to launch SU2_CFD with customized unsteady boundary conditions using the Python wrapper.
#  \author David Thomas
#  \version 7.5.0 "Blackbird"
#
# SU2 Project Website: https://su2code.github.io
#
# The SU2 Project is maintained by the SU2 Foundation
# (http://su2foundation.org)
#
# Copyright 2012-2022, SU2 Contributors (cf. AUTHORS.md)
#
# SU2 is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# SU2 is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with SU2. If not, see <http://www.gnu.org/licenses/>.

# ----------------------------------------------------------------------
#  Imports
# ----------------------------------------------------------------------

import sys
from optparse import OptionParser  # use a parser for configuration
import pysu2                  # imports the SU2 wrapped module
from math import *
import numpy
import precice
from time import sleep
# -------------------------------------------------------------------
#  Main
# -------------------------------------------------------------------

def main():

    # Command line options
    parser=OptionParser()
    parser.add_option("-f", "--file", dest="filename", help="Read config from FILE", metavar="FILE")
    parser.add_option("--parallel", action="store_true",
                    help="Specify if we need to initialize MPI", dest="with_MPI", default=False)

    # preCICE options with default settings
    parser.add_option("-p", "--precice-participant", dest="precice_name", help="Specify preCICE participant name", default="Fluid" )
    parser.add_option("-c", "--precice-config", dest="precice_config", help="Specify preCICE config file", default="../precice-config.xml")
    parser.add_option("-m", "--precice-mesh", dest="precice_mesh", help="Specify the preCICE mesh name", default="Fluid-Mesh")

    # Dimension
    parser.add_option("-d", "--dimension", dest="nDim", help="Dimension of fluid domain", type="int", default=3)
  
    (options, args) = parser.parse_args()
    options.nZone = int(1)

    # Import mpi4py for parallel run
    if options.with_MPI == True:
        from mpi4py import MPI
        comm = MPI.COMM_WORLD
        rank = comm.Get_rank()
    else:
        comm = 0
        rank = 0

    # Initialize the corresponding driver of SU2, this includes solver preprocessing
    try:
        SU2Driver = pysu2.CSinglezoneDriver(options.filename, options.nZone, comm);
    except TypeError as exception:
        print('A TypeError occured in pysu2.CDriver : ',exception)
        if options.with_MPI == True:
            print('ERROR : You are trying to initialize MPI with a serial build of the wrapper. Please, remove the --parallel option that is incompatible with a serial build.')
        else:
            print('ERROR : You are trying to launch a computation without initializing MPI but the wrapper has been built in parallel. Please add the --parallel option in order to initialize MPI for the wrapper.')
        return

    # Configure preCICE:
    size = comm.Get_size()
    try:
        interface = precice.Interface(options.precice_name, options.precice_config, rank, size)#, comm)
    except:
        print("There was an error configuring preCICE")
        return

    # Check preCICE + SU2 dimensions
    if options.nDim != interface.get_dimensions():
        print("SU2 and preCICE dimensions are not the same! Exiting")
        return
    
    #Setup moving mesh
    ################################################################################
    MovingMarkerID = None
    MovingMarker = 'interface'       #specified by the user

    # Get all the tags with the moving option
    MovingMarkerList =  SU2Driver.GetAllDeformMeshMarkersTag()

    # Get all the markers defined on this rank and their associated indices.
    allMarkerIDs = SU2Driver.GetAllBoundaryMarkers()

    # Check if the specified marker has a moving option and if it exists on this rank.
    if MovingMarker in MovingMarkerList and MovingMarker in allMarkerIDs.keys():
        MovingMarkerID = allMarkerIDs[MovingMarker]

    # Number of vertices on the specified marker (per rank)
    nVertex_MovingMarker = 0         #total number of vertices (physical + halo)
    nVertex_MovingMarker_HALO = 0    #number of halo vertices
    nVertex_MovingMarker_PHYS = 0    #number of physical vertices
    iVertices_MovingMarker_PHYS = [] # indices of vertices this rank is working on
    # Datatypes must be primitive as input to SU2 wrapper code, not numpy.int8, numpy.int64, etc.. So a list is used
    
    if MovingMarkerID != None:
        nVertex_MovingMarker = SU2Driver.GetNumberVertices(MovingMarkerID)
        nVertex_MovingMarker_HALO = SU2Driver.GetNumberHaloVertices(MovingMarkerID)
        nVertex_MovingMarker_PHYS = nVertex_MovingMarker - nVertex_MovingMarker_HALO
        
        # Obtain indices of all vertices that are being worked on on this rank
        for iVertex in range(nVertex_MovingMarker):
            if not SU2Driver.IsAHaloNode(MovingMarkerID, iVertex):
                iVertices_MovingMarker_PHYS.append(int(iVertex))
                
    #####################
    MovingMarkerID2 = None
    MovingMarker2 = 'interface2'       #specified by the user

    # Get all the tags with the moving option
    MovingMarkerList =  SU2Driver.GetAllDeformMeshMarkersTag()

    # Get all the markers defined on this rank and their associated indices.
    allMarkerIDs = SU2Driver.GetAllBoundaryMarkers()

    # Check if the specified marker has a moving option and if it exists on this rank.
    if MovingMarker2 in MovingMarkerList and MovingMarker2 in allMarkerIDs.keys():
        MovingMarkerID2 = allMarkerIDs[MovingMarker2]

    # Number of vertices on the specified marker (per rank)
    nVertex_MovingMarker2 = 0         #total number of vertices (physical + halo)
    nVertex_MovingMarker_HALO2 = 0    #number of halo vertices
    nVertex_MovingMarker_PHYS2 = 0    #number of physical vertices
    iVertices_MovingMarker_PHYS2 = [] # indices of vertices this rank is working on
    # Datatypes must be primitive as input to SU2 wrapper code, not numpy.int8, numpy.int64, etc.. So a list is used
    
    if MovingMarkerID2 != None:
        nVertex_MovingMarker2 = SU2Driver.GetNumberVertices(MovingMarkerID2)
        nVertex_MovingMarker_HALO2 = SU2Driver.GetNumberHaloVertices(MovingMarkerID2)
        nVertex_MovingMarker_PHYS2 = nVertex_MovingMarker2 - nVertex_MovingMarker_HALO2
        
        # Obtain indices of all vertices that are being worked on on this rank
        for iVertex in range(nVertex_MovingMarker2):
            if not SU2Driver.IsAHaloNode(MovingMarkerID2, iVertex):
                iVertices_MovingMarker_PHYS2.append(int(iVertex))
    ################################################################################
      
    #Setup CHT
    ################################################################################
    CHTMarkerID = None
    CHTMarker = 'interface' # Name of CHT marker to couple

    # Get all the tags with the CHT option
    CHTMarkerList =  SU2Driver.GetAllCHTMarkersTag()

    # Get all the markers defined on this rank and their associated indices.
    allMarkerIDs = SU2Driver.GetAllBoundaryMarkers() # Returns all markers defined on this rank

    #Check if the specified marker has a CHT option and if it exists on this rank.
    if CHTMarker in CHTMarkerList and CHTMarker in allMarkerIDs.keys():
      CHTMarkerID = allMarkerIDs[CHTMarker] # So: if CHTMarkerID != None, then it exists on this rank
    
    # Number of vertices on the specified marker (per rank)
    nVertex_CHTMarker = 0         #total number of vertices (physical + halo) on this rank
    nVertex_CHTMarker_HALO = 0    #number of halo vertices
    nVertex_CHTMarker_PHYS = 0    #number of physical vertices
    iVertices_CHTMarker_PHYS = [] #indices of vertices this rank is working on
    # Note: Datatypes must be primitive as input to SU2 wrapper code, not numpy.int8, numpy.int64, etc.. So a list is used

    # If the CHT marker is defined on this rank:
    if CHTMarkerID != None:
      nVertex_CHTMarker = SU2Driver.GetNumberVertices(CHTMarkerID) #Total number of vertices on the marker
      nVertex_CHTMarker_HALO = SU2Driver.GetNumberHaloVertices(CHTMarkerID)
      nVertex_CHTMarker_PHYS = nVertex_CHTMarker - nVertex_CHTMarker_HALO

      # Obtain indices of all vertices that are being worked on on this rank
      for iVertex in range(nVertex_CHTMarker):
        if not SU2Driver.IsAHaloNode(CHTMarkerID, iVertex):
          iVertices_CHTMarker_PHYS.append(int(iVertex))
    ################################################################################
    
    # Get preCICE mesh ID
    try:
        mesh_id = interface.get_mesh_id(options.precice_mesh)
        mesh_id2 = interface.get_mesh_id("Fluid-Mesh2")
    except:
        print("Invalid or no preCICE mesh name provided")
        return
    
    # Get coords of vertices
    coords2 = numpy.zeros((nVertex_MovingMarker_PHYS2, options.nDim))
    for i, iVertex in enumerate(iVertices_MovingMarker_PHYS2):
        coord_passive = SU2Driver.GetInitialMeshCoord(MovingMarkerID2, iVertex)
        for iDim in range(options.nDim):
            coords2[i, iDim] = coord_passive[iDim]
    
    # Get coords of vertices
    coords = numpy.zeros((nVertex_CHTMarker_PHYS, options.nDim))
    for i, iVertex in enumerate(iVertices_CHTMarker_PHYS):
      coord_passive = SU2Driver.GetInitialMeshCoord(CHTMarkerID, iVertex)
      for iDim in range(options.nDim):
        coords[i, iDim] = coord_passive[iDim]

    # Set mesh vertices in preCICE:
    vertex_ids = interface.set_mesh_vertices(mesh_id, coords)
    vertex_ids2 = interface.set_mesh_vertices(mesh_id2, coords2)

    # Get read and write data IDs
    # By default:
    precice_read = "Displacement"
    precice_write = "Pressure"
    read_data_id = interface.get_data_id(precice_read, mesh_id)
    read_data_id2 = interface.get_data_id(precice_read, mesh_id2)
    write_data_id = interface.get_data_id(precice_write, mesh_id)
    
    #add CHT part######################################
    precice_read_CHT = "Temperature"
    precice_write_CHT = "Heat-Flux"
    GetFxn = SU2Driver.GetVertexNormalHeatFlux
    SetFxn = SU2Driver.SetVertexTemperature
    GetInitialFxn = SU2Driver.GetVertexTemperature
    read_data_id_CHT = interface.get_data_id(precice_read_CHT, mesh_id)
    write_data_id_CHT = interface.get_data_id(precice_write_CHT, mesh_id)
    ###################################################

    # Instantiate arrays to hold displacements + forces info
    displacements = numpy.zeros((nVertex_MovingMarker_PHYS,options.nDim))
    displacements2 = numpy.zeros((nVertex_MovingMarker_PHYS2,options.nDim))
    pressure = numpy.zeros((nVertex_MovingMarker_PHYS))
    read_data = numpy.zeros(nVertex_CHTMarker_PHYS)
    write_data = numpy.zeros(nVertex_CHTMarker_PHYS)

    # Retrieve some control parameters from the driver
    deltaT = SU2Driver.GetUnsteady_TimeStep()
    TimeIter = SU2Driver.GetTime_Iter()
    nTimeIter = SU2Driver.GetnTimeIter()
    time = TimeIter*deltaT

    # Setup preCICE dt:
    precice_deltaT = interface.initialize()

    # Set up initial data for preCICE
    if (interface.is_action_required(precice.action_write_initial_data())):
        for i, iVertex in enumerate(iVertices_MovingMarker_PHYS):
            pressure[i] = SU2Driver.GetVertexPressure(MovingMarkerID, iVertex)
            
        for i, iVertex in enumerate(iVertices_CHTMarker_PHYS):
          write_data[i] = GetInitialFxn(CHTMarkerID, iVertex)

        interface.write_block_scalar_data(write_data_id, vertex_ids, pressure)
        interface.write_block_scalar_data(write_data_id_CHT, vertex_ids, write_data)
        interface.mark_action_fulfilled(precice.action_write_initial_data())

    interface.initialize_data()

    # Sleep briefly to allow for data initialization to be processed
    sleep(3)

    # Time loop is defined in Python so that we have acces to SU2 functionalities at each time step
    if rank == 0:
        print("\n------------------------------ Begin Solver -----------------------------\n")
    sys.stdout.flush()
    if options.with_MPI == True:
        comm.Barrier()

    precice_saved_time = 0
    precice_saved_iter = 0
    while (interface.is_coupling_ongoing()):#(TimeIter < nTimeIter):
        
        # Implicit coupling
        if (interface.is_action_required(precice.action_write_iteration_checkpoint())):
            # Save the state
            SU2Driver.SaveOldState()
            precice_saved_time = time
            precice_saved_iter = TimeIter
            interface.mark_action_fulfilled(precice.action_write_iteration_checkpoint())

        if (interface.is_read_data_available()):
            # Retreive data from preCICE
            displacements = interface.read_block_vector_data(read_data_id, vertex_ids)
            displacements2 = interface.read_block_vector_data(read_data_id2, vertex_ids2)
            read_data = interface.read_block_scalar_data(read_data_id_CHT, vertex_ids) 
            
            # Set the updated displacements
            for i, iVertex in enumerate(iVertices_MovingMarker_PHYS):
                DisplX = displacements[i][0]
                DisplY = displacements[i][1]
                DisplZ = 0 if options.nDim == 2 else displacements[i][2]

                SU2Driver.SetMeshDisplacement(MovingMarkerID, iVertex, DisplX, DisplY, DisplZ)
                
            for i, iVertex in enumerate(iVertices_MovingMarker_PHYS2):
                DisplX = displacements2[i][0]
                DisplY = displacements2[i][1]
                DisplZ = 0 if options.nDim == 2 else displacements2[i][2]

                SU2Driver.SetMeshDisplacement(MovingMarkerID2, iVertex, DisplX, DisplY, DisplZ)
                
            # Set the updated values
            for i, iVertex in enumerate(iVertices_CHTMarker_PHYS):
                SetFxn(CHTMarkerID, iVertex, read_data[i])

            # Tell the SU2 drive to update the boundary conditions
            SU2Driver.BoundaryConditionsUpdate()
        
        if options.with_MPI == True:
            comm.Barrier()
            
        # Update timestep based on preCICE
        deltaT = SU2Driver.GetUnsteady_TimeStep()
        deltaT = min(precice_deltaT, deltaT)
        SU2Driver.SetUnsteady_TimeStep(deltaT)
        
        # Time iteration preprocessing (mesh is deformed here)
        SU2Driver.Preprocess(TimeIter)

        # Run one time iteration (e.g. dual-time)
        SU2Driver.Run()

        # Postprocess the solver
        SU2Driver.Postprocess()

        # Update the solver for the next time iteration
        SU2Driver.Update()

        # Monitor the solver and output solution to file if required
        stopCalc = SU2Driver.Monitor(TimeIter)


        if (interface.is_write_data_required(deltaT)):
            # Loop over the vertices
            for i, iVertex in enumerate(iVertices_MovingMarker_PHYS):
                # Get forces at each vertex
                pressure[i] = SU2Driver.GetVertexPressure(MovingMarkerID, iVertex)

            # Write data to preCICE
            interface.write_block_scalar_data(write_data_id, vertex_ids, pressure)
            
            # Loop over the vertices
            for i, iVertex in enumerate(iVertices_CHTMarker_PHYS):
              # Get heat fluxes at each vertex
              write_data[i] = GetFxn(CHTMarkerID, iVertex)
              
            # Write data to preCICE
            interface.write_block_scalar_data(write_data_id_CHT, vertex_ids, write_data)

        # Advance preCICE
        precice_deltaT = interface.advance(deltaT)


        # Implicit coupling:
        if (interface.is_action_required(precice.action_read_iteration_checkpoint())):
            # Reload old state
            SU2Driver.ReloadOldState()
            time = precice_saved_time
            TimeIter = precice_saved_iter
            interface.mark_action_fulfilled(precice.action_read_iteration_checkpoint())
        else: # Output and increment as usual
            SU2Driver.Output(TimeIter)
            if (stopCalc == True):
                break
            # Update control parameters
            TimeIter += 1
            time += deltaT
        
        if options.with_MPI == True:
            comm.Barrier()
    # Postprocess the solver and exit cleanly
    SU2Driver.Postprocessing()

    interface.finalize()

    if SU2Driver != None:
        del SU2Driver

# -------------------------------------------------------------------
#  Run Main Program
# -------------------------------------------------------------------

# this is only accessed if running from command prompt
if __name__ == '__main__':
    main()
