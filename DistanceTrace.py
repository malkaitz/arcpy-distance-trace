"""
Script documentation

- Tool parameters are accessed using arcpy.GetParameter() or 
                                     arcpy.GetParameterAsText()
- Update derived parameter values using arcpy.SetParameter() or
                                        arcpy.SetParameterAsText()
"""
import arcpy
import math
import os

def create_line_geometry_object(vertices): #vertices [(x,y), (x,y)...]
    line_geometry_object = arcpy.Polyline(
            arcpy.Array([arcpy.Point(*coords) for coords in vertices]))
    return line_geometry_object

def script_tool(lines, sql, distance):

    arcpy.AddMessage(lines, sql, distance)

    return

def path_length (path):
    catA = path[0][0] - path[1][0]
    catB = path[0][1] - path[1][1]
    return math.hypot(catA, catB)
   

def get_other_value(point, path):  
    # Check if the parameter is in the list and return the other value
    if point in path:
        return path[1] if point== path[0] else path[0]
    else:
        return None  # Return None or raise an error if the parameter is not valid

def find_lines(point, data_dict): # {(x,y): [{'oid': OID_1, 'vertices': [(x,y), (x,y)]}, {'oid':OID_2, 'vertices': [(x,y), (x,y)], ....]],....}
    paths_data = data_dict[point] #[{'oid': OID_1, 'vertices': [(x,y), (x,y)]}, {'oid':OID_2, 'vertices': [(x,y), (x,y)]}, ....]], ....]
    return paths_data

def trace(point, way, count): #way UP, DOWN, BOTH

    founded_lines_data = find_lines(point, vertices_path_dict) # [{}, {},...]    
    
    for dict_data in founded_lines_data:
               
        path = dict_data['vertices']  
        #arcpy.AddMessage(path)

        start_vertex = path[0]
        end_vertex = path[1]
        way_point = {'UP' : end_vertex , 'DOWN' : start_vertex}
        the_vertex = way_point[way]

        if point == the_vertex and dict_data['oid']  not in traced_lines_oids_list: 
            traced_lines_oids_list.append(dict_data['oid'])        

            length = path_length(path)
            arcpy.AddMessage(f'current path length : {length}')
            arcpy.AddMessage(f'function param count: {count}')
            #get added_count variable !!!!!!!!IMPORTANT!!!!!!
            added_count = count + length             
            arcpy.AddMessage(f'added_count + length : {count}')
            
            arcpy.AddMessage(f'selected path : {path}')

            if added_count < float(distance):  
                the_other_point = get_other_value(point, path)
                
                traced_vertices_paths.append(path)          
                trace(the_other_point, way, added_count)            

            else:            
                # create line geom with last path
                path_geom = create_line_geometry_object(path)
                arcpy.AddMessage(f'path_geom first point: {path_geom.firstPoint}')
                arcpy.AddMessage(f'last path : {path}')
                plus_distance = added_count - float(distance)
                arcpy.AddMessage(f'plus distance : {plus_distance}')
                len_path = path_length(path)
                arcpy.AddMessage(f'length last path : {len_path}')

                if way == 'UP':
                    math_plus_distance   = plus_distance
                    last_path_vertex = path[1]
                else:
                    math_plus_distance = len_path - plus_distance 
                    last_path_vertex = path[0]  

                the_last_point = path_geom.positionAlongLine(math_plus_distance)   #Returns a point on a line at a specified distance from the beginning of the line.
                
                x_last = the_last_point.firstPoint.X
                y_last = the_last_point.firstPoint.Y
                traced_vertices_paths.append([last_path_vertex, (x_last, y_last)])

                arcpy.AddMessage(f'last point {(x_last, y_last)}\n')  

traced_lines_oids_list = []


if __name__ == "__main__":

    project = arcpy.mp.ArcGISProject("CURRENT")
    gdb_path = project.defaultGeodatabase
    arcpy.env.overwriteOutput = True
    map_obj = project.activeMap

    points = arcpy.GetParameterAsText(0)
    lines = arcpy.GetParameterAsText(1)
    sql= arcpy.GetParameterAsText(2)
    distance = arcpy.GetParameterAsText(3)
    way =  arcpy.GetParameterAsText(4)

    #---------get start point vertex. it is a selected point in the map-----
    point_vertex = [] #[(x,y)]
    with arcpy.da.SearchCursor(points , ['SHAPE@XY', 'OID@']) as cursor:  
        for row in cursor: 
            point_vertex.append(row[0])             
            
    del cursor

    #arcpy.AddMessage(point_vertex[0])

    #----------get distance buffer-----------
    # get coordinate system units
    layer_desc = arcpy.Describe(points)
    spatial_ref = layer_desc.spatialReference
    linear_units = spatial_ref.linearUnitName

    arcpy.AddMessage(linear_units)
    
    # get point geometry
    x = point_vertex[0][0]
    y = point_vertex[0][1]
    pt = arcpy.Point(x, y)
    point_geometry = arcpy.PointGeometry(pt)

    # Output buffer polygon in memory
    output_buffer = "in_memory/buffer_output"

    # Run the buffer tool
    arcpy.Buffer_analysis(point_geometry, output_buffer, distance)

    #--------get lines in buffer------------------
    # select the lines with the param sql
    arcpy.SelectLayerByAttribute_management(lines, 
                                            "NEW_SELECTION", 
                                            sql)

    # Select features from the target layer that intersect the buffer
    arcpy.management.MakeFeatureLayer(output_buffer, "buffer_lyr")
    arcpy.SelectLayerByLocation_management(in_layer=lines, 
                                           overlap_type="INTERSECT", 
                                           select_features="buffer_lyr",  
                                           selection_type="SUBSET_SELECTION")

    # Get the count of selected features
    selected_count = arcpy.GetCount_management(lines)
    arcpy.AddMessage(selected_count)

    # Build vertices dictionary
    # {(x,y): [{OID:[(x,y), (x,y),...]}, {OID: [(x,y), (x,y),...]},.......], .....}
    lines_dict = {}       
    with arcpy.da.SearchCursor(lines , ['OID@','Shape@']) as cursor:  
        for row in cursor:                     
            line_geometry = []   #[(x,y), (x,y),...]   
            singlePart = row[1].getPart(0)  
            for pointObject in singlePart:
                x = pointObject.X
                y = pointObject.Y
                vertex = (x,y)            
                line_geometry.append(vertex)
            # make a dict for every vertex in line
            for vertex in line_geometry:
                vertex_dict = {} # {OID:[(x,y), (x,y),...]}
                vertex_dict[row[0]]= line_geometry
                # Add vertex dict to lines dict. If vertex exists add line to the list value.
                if vertex not in lines_dict: 
                    # lines_dict[vertex] is a list
                    lines_dict[vertex] = [vertex_dict]
                else:
                    lines_dict[vertex].append(vertex_dict) 
    del cursor     

    # build paths dictionary from vertices dictionary
    # {(x,y): [{OID_1: [(x,y), (x,y)]}, {OID_2: [(x,y), (x,y)]}, ....],....}
    
    paths_dict = {} #{OID_1: [(x,y), (x,y)], OID_2: [(x,y), (x,y)], ....}
    with arcpy.da.SearchCursor(lines , ['OID@','Shape@']) as cursor:  
        for row in cursor:                     
            line_geometry = []   #[(x,y), (x,y),...]   
            singlePart = row[1].getPart(0)  
            for pointObject in singlePart:
                x = pointObject.X
                y = pointObject.Y
                vertex = (x,y)            
                line_geometry.append(vertex)
            # Create pairs of consecutive vertices
            paths_list = [[line_geometry[i], line_geometry[i+1]] for i in range(len(line_geometry) - 1)]
            """""
            for vertex in line_geometry:
                vertex_index = line_geometry.index(vertex)
                vertices_count = len(line_geometry)
                if vertex_index < vertices_count -1:
                    next_vertex = line_geometry[vertex_index + 1]
                    path = [vertex, next_vertex ]
            """""
            
            prefix = 0
            for path in paths_list:                                
                path_oid = str(row[0]) + '_' + str(prefix)
                
                paths_dict[path_oid] = path
                prefix += 1

    arcpy.SelectLayerByAttribute_management(lines, 
                                            "CLEAR_SELECTION"
                                            )
            
    # get touching paths for every vertex   
    vertices_path_dict = {} #{(x,y): [{'oid': OID_1, 'vertices': [(x,y), (x,y)]}, {'oid':OID_2, 'vertices': [(x,y), (x,y)]}, ....],....}
    for key, value in paths_dict.items():
        for vertex in value:
            data_dict_list = [] # [{'oid': OID_1, 'vertices': [(x,y), (x,y)]}, {'oid':OID_2, 'vertices': [(x,y), (x,y)]}, ....]]
            #find the paths for the vertex
            for oid_, vertices_list in paths_dict.items():
                if vertex in vertices_list:
                    data_dict_list.append({'oid' : oid_ , 'vertices': vertices_list})
            if vertex not in vertices_path_dict:
                vertices_path_dict[vertex] = data_dict_list
            else:                
                for path_dict in data_dict_list:
                    if path_dict not in vertices_path_dict[vertex]:
                        vertices_path_dict[vertex].append(path_dict)

    traced_vertices_paths = []
    trace(point_vertex[0], way, 0)
    arcpy.AddMessage(traced_vertices_paths)

    arcpy.AddMessage(traced_lines_oids_list)
    
    main_array = arcpy.Array()
    # Loop through each path (list of vertices)
    for path in traced_vertices_paths:
        # Create an empty array for this path
        path_array = arcpy.Array()
        
        # Loop through each (x, y) pair in the path and create Point objects
        for x, y in path:
            point = arcpy.Point(x, y)
            path_array.add(point)
        
        # Add the path (array of points) to the main array
        main_array.add(path_array)

    # Create a polyline geometry from the main array of paths
    polyline = arcpy.Polyline(main_array, spatial_ref)

    # Clean up the array objects
    main_array.removeAll()

    arcpy.CopyFeatures_management(polyline, os.path.join(gdb_path, 'result_geom'))

    # Clean up the array objects
    main_array.removeAll()

    

    #script_tool(param0, param1)
    #arcpy.SetParameterAsText(2, "Result")

    