import datetime
import requests, zipfile, io
import geopandas as gpd
import rioxarray
import numpy as np
import matplotlib.pyplot as plt
import matplotlib

def grab_data(in_option,in_date):
    print('Downloading data...')
    case_list=['1day','last7days','last14days','last30days','last60days','last90days','last180days','last365days','month2date','year2date','wateryear2date']
    filename_case_list=['1day','last7days','last14days','last30days','last60days','last90days','last180days','last365days','mtd','ytd','wytd']
    try:
        f=requests.get('https://water.weather.gov/precip/downloader.php?date='+str(in_date)+'&file_type=geotiff&range='+str(case_list[int(in_option)-1])+'&format=zip')
        print("File downloaded successfully.")
    except:
        print("Error downloading file.")
    try:
        f=zipfile.ZipFile(io.BytesIO(f.content)).open('nws_precip_'+str(filename_case_list[int(in_option)-1])+'_'+str(in_date)+'_conus.tif')
        print("TIF file loaded.")
    except:
        print("Error extracting Zipfile.")
        exit()
    fname=str(in_date)+'-'+str(case_list[int(in_option)-1])+'.png'
    return f,fname

def lat_lon_from_hrap(hrap_x, hrap_y):

    raddeg = 57.29577951
    earthrad = 6371.2
    stdlon = 105.
    mesh_len = 4.7625

    tlat = 60. / raddeg

    x = hrap_x - 401.
    y = hrap_y - 1601.
    rr = x * x + y * y
    gi = ((earthrad * (1 + np.sin(tlat))) / mesh_len)
    #gi = gi * gi
    ll_y = (np.pi/2-2*np.arctan2(np.sqrt(rr),gi))*raddeg
    #ll_y = np.arcsin((gi - rr) / (gi + rr)) * raddeg
    ang = np.arctan2(y, x) * raddeg
    if (ang < 0):
        ang = ang+360.
    ll_x = 270 + stdlon - ang
    if (ll_x < 0):
        ll_x = ll_x + 360
    if (ll_x > 360):
        ll_x = ll_x - 360
    return ll_x, ll_y


def cut_data(in_file):
    try:
        print("Reading NWS data and processing HRAP coordinates to lat/long.")
        rds=rioxarray.open_rasterio(in_file)
        lats = np.empty((881, 1121), dtype='float')
        lons = np.empty((881, 1121), dtype='float')
        HRAP_XOR = 0
        HRAP_YOR = 0
        for i in range(881):
            for j in range(1121):
                hrap_x = j + HRAP_XOR + 0.5
                hrap_y = i + HRAP_YOR + 0.5
                lon, lat = lat_lon_from_hrap(hrap_x, hrap_y)
                lats[880-i,j] = lat
                lons[880-i,j] = -lon
        rds.name="data"
        df = rds[0].to_dataframe().reset_index()
        geometry = gpd.points_from_xy(lons.flatten(), lats.flatten())
        gdf = gpd.GeoDataFrame(df, crs="EPSG:4326", geometry=geometry)
        #gdf.set_crs(crs="EPSG:4326",allow_override='True')
        fp = "./Ky_County_Lines.shp"
        # Read file using gpd.read_file()
        data = gpd.read_file(fp)
    except:
        print("Unable to convert NWS data to usable format.")
        exit()
    try:
        print("Clipping NWS data to Kentucky map outline.")
        points=gpd.clip(gdf,data.to_crs(epsg=4326).geometry)
    except:
        print("Unable to cut data.")
        exit()
    return points,data

def create_plot(in_points,in_map,in_option,fname):
    print("Generating plot...")
    cmaplist=["#9a9a9a",
    "#4bd2f7",
    "#6aa0d0",
    "#3c4bac",
    "#3cf74b",
    "#3cb447",
    "#3c8743",
    "#f7f73c",
    "#fbde88",
    "#f7ac3c",
    "#f73c3c",
    "#bf3c3c",
    "#9a3c3c",
    "#f73cf7",
    "#9a74e5",
    "#e1e1e1"]
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list('Custom cmap', cmaplist)
    max_rain=in_points['data'].max()
    if max_rain>50:
        ticks = ['',.01,2.5,5.0,10,15,20,25,30,35,40,50,60,70,80,100,'']
        bounds = [0,.01,2.5,5.0,10,15,20,25,30,35,40,50,60,70,80,100,1e200]
    elif max_rain>20:
        ticks = ['',.01,.50,1.0,2.0,4.0,6.0,8.0,10.0,15.0,20.0,25.0,30.0,35.0,40.0,50.0,'']
        bounds = [0,.01,.50,1.0,2.0,4.0,6.0,8.0,10.0,15.0,20.0,25.0,30.0,35.0,40.0,50.0,1e200]
    elif max_rain>10:
        ticks = ['',.01,.10,.25,.50,1.0,1.5,2.0,3.0,4.0,5.0,6.0,8.0,10,15,20,'']
        bounds = [0,.01,.10,.25,.50,1.0,1.5,2.0,3.0,4.0,5.0,6.0,8.0,10,15,20,1e200]
    else:
        ticks = ['',.01,.10,.25,.50,.75,1.0,1.5,2.0,2.5,3.0,4.0,5.0,6.0,8.0,10,'']
        bounds = [0,.01,.10,.25,.50,.75,1.0,1.5,2.0,2.5,3.0,4.0,5.0,6.0,8.0,10,1e200]
    norm = matplotlib.colors.BoundaryNorm(bounds, cmap.N)
    in_points.data[in_points.data<=.010]=np.nan
    fig, ax = plt.subplots(1, 1,figsize=(25,25))
    in_points.plot(column='data',cmap=cmap,norm=norm,markersize=60,marker='o',ax=ax)
    in_map.to_crs(epsg=4326).plot(facecolor='none',edgecolor='black',ax=ax)
    cbar=plt.colorbar(ax.get_children()[0],shrink=0.35,cmap=cmap,norm=norm,ticks=bounds)
    cbar.ax.set_yticklabels(ticks)
    plt.axis('off')
    plt.savefig(fname,dpi=300,bbox_inches='tight',facecolor='White')


print("Which time span would you like to produce a map for?")
print(" -------------------------------------------------- ")
print("   1) 1 Day")
print("   2) Last 7 Days")
print("   3) Last 14 Days")
print("   4) Last 30 Days")
print("   5) Last 60 Days")
print("   6) Last 90 Days")
print("   7) Last 180 Days")
print("   8) Last 365 Days")
print("   9) Month to Date")
print("  10) Year to Date")
print("  11) Water Year to Date")
print(" ")
pick=input()
toggle=0
while toggle==0:
    try:
        int(pick)
        if int(pick)<=11:
            toggle=1
        else:
            print("Please input a number corresponding to an option above.")
            pick=input()
    except:
        print("Incorrect input, please input a number corresponding to an option above.")
        pick=input()
toggle=0

while toggle==0:
    date=input("Please input the ending date in the format YYYYMMDD, if not input detected today's date will be used ("+str(datetime.datetime.now().strftime("%Y%m%d"))+").\n")
    print(date)
    if date=="":
        date=datetime.datetime.now().strftime("%Y%m%d")
    try:
        datetime.datetime.strptime(date, '%Y%m%d')
        toggle=1
    except:
        print("Incorrect date format, should be YYYYMMDD.")
toggle=0
data,fname=grab_data(pick,date)
points,kymap=cut_data(data)
create_plot(points,kymap,pick,fname)