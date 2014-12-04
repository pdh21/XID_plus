import numpy as np
import astropy
from astropy.io import fits
from astropy import wcs
import pickle
import dill
import XIDp_mod_beta as xid_mod
from astropy import coordinates as coord
from astropy import units as u
from astropy.coordinates import Angle

#Get field names out of ALMA data catalogue:
fields=[]
sources=[]
ra_list=[]
dec_list=[]
file=open('/Users/jillianscudder/Research/ALMA_XID/table_observed.dat', 'r')
dat=file.readlines()
for entry in dat[1::]:
    splitlines=entry.split()
    fields.append(splitlines[0])
    sources.append(splitlines[1])
    ra_list.append(splitlines[2])
    dec_list.append(splitlines[3])
file.close()
fields=np.asarray(fields)
sources=np.asarray(sources)
ra_list=np.asarray(ra_list)
dec_list=np.asarray(dec_list)

#Find the unique field IDs
unique_fields=np.unique(fields)
print 'Number of fields:', len(unique_fields)
#Select the number of sources per field
sources_per_field={}
ra_per_field={}
dec_per_field={}
for u_field in unique_fields:
    sources_per_field[u_field]=sources[np.where(fields==u_field)]
    ra_per_field[u_field]=ra_list[np.where(fields==u_field)]
    dec_per_field[u_field]=dec_list[np.where(fields==u_field)]


#Convert RA/Dec lists into decimal from hours
ra_decdeg_dict={}
dec_decdeg_dict={}
sources=sources_per_field[unique_fields[0]]
ratemp=ra_per_field[unique_fields[0]]
dectemp=dec_per_field[unique_fields[0]]
for index, entry in enumerate(ratemp):
    source=sources[index]
    ra_temp=Angle(entry, unit=u.hour)
    dec_temp=Angle(dectemp[index], unit=u.deg)
    ra_decdeg_dict[source]=(ra_temp.to_string(unit='degree', decimal='True', precision=7))
    dec_decdeg_dict[source]=(dec_temp.to_string(unit='degree', decimal='True', precision=7))

#Folder containing maps
imfolder='/Users/jillianscudder/Research/ALMA_XID/'
#field
field=fields[0]

# In[7]:

pswfits=imfolder+'SPIRE250/'+field+'_250.fits'#SPIRE 250 map
pmwfits=imfolder+'SPIRE350/'+field+'_350.fits'#SPIRE 350 map
plwfits=imfolder+'SPIRE500/'+field+'_500.fits'#SPIRE 500 map


# In[8]:
##I think my prior catalogue is the 870 source positions, already read in
prior_cat="870 positions"
"""
#Folder containing prior input catalogue
folder="/research/astrodata/fir/hermes/www/xid/rel0712/"
#prior catalogue
prior_cat="mod_cosmos-xid-pepprior-0512.fits.gz"
hdulist = fits.open(folder+prior_cat)
fcat=hdulist[1].data
hdulist.close()
inra=fcat['INRA']
indec=fcat['INDEC']
f_src=fcat['F250']
df_src=f_src
nrealcat=fcat.size
bkg250=fcat['bkg250'][0]
bkg350=fcat['bkg350'][0]
bkg500=fcat['bkg500'][0]
"""
# Open images and noise maps and use WCS module in astropy to get header information

# In[9]:

#-----250-------------
hdulist = fits.open(pswfits, ignore_missing_end=True)
im250phdu=hdulist[0].header
im250=(hdulist[1].data*1.0E3)
nim250=hdulist[2].data[1]*1.0E3
w_250 = wcs.WCS(hdulist[1].header)
pixsize250=3600.0*w_250.wcs.cd[1,1] #pixel size (in arcseconds)
print 'Arcseconds per pixel, 250 micron:', pixsize250
hdulist.close()
#-----350-------------
hdulist = fits.open(pmwfits, ignore_missing_end=True)
im350phdu=hdulist[0].header
im350=hdulist[1].data*1.0E3
nim350=hdulist[2].data[1]*1.0E3
w_350 = wcs.WCS(hdulist[1].header)
pixsize350=3600.0*w_350.wcs.cd[1,1] #pixel size (in arcseconds)
print 'Arcseconds per pixel, 350 micron:', pixsize350
hdulist.close()
#-----500-------------
hdulist = fits.open(plwfits, ignore_missing_end=True)
im500phdu=hdulist[0].header
im500=hdulist[1].data*1.0E3
nim500=hdulist[2].data[1]*1.0E3
w_500 = wcs.WCS(hdulist[1].header)
pixsize500=3600.0*w_500.wcs.cd[1,1] #pixel size (in arcseconds)
print 'Arcseconds per pixel, 500 micron:', pixsize500
hdulist.close()

# Since I am only testing, redo this so that I only fit sources within a given range of the mean ra and dec position of the prior list

# In[12]:
#Count number of sources per object:
fieldid=unique_fields[0]
ralist=[]
declist=[]
sourcelist=sources_per_field[fieldid]
for entry in sourcelist:
    ralist.append(float(ra_decdeg_dict[entry]))
    declist.append(float(dec_decdeg_dict[entry]))

print 'Fitting '+str(len(ralist))+' sources...'

inra=np.asarray(ralist)
indec=np.asarray(declist)

# Point response information, at the moment its 2D Gaussian, but should be general. All lstdrv_solvfluxes needs is 2D array with prf

# In[15]:

#pixsize array (size of pixels in arcseconds)
pixsize=np.array([pixsize250,pixsize350,pixsize500])
#point response function for the three bands
prfsize=np.array([18.15,25.15,36.3])
#set fwhm of prfs in terms of pixels
pfwhm=prfsize/pixsize
#set size of prf array (in pixels)
paxis=[13,13]
#use Gaussian2DKernel to create prf (requires stddev rather than fwhm hence pfwhm/2.355)
from astropy.convolution import Gaussian2DKernel
print 'Pixelsize', pixsize
print 'Standard deviation for Gaussian', pfwhm[0]/2.355
prf250=Gaussian2DKernel(pfwhm[0]/2.355,x_size=paxis[0],y_size=paxis[1])
prf250.normalize(mode='peak')
prf350=Gaussian2DKernel(pfwhm[1]/2.355,x_size=paxis[0],y_size=paxis[1])
prf350.normalize(mode='peak')
prf500=Gaussian2DKernel(pfwhm[2]/2.355,x_size=paxis[0],y_size=paxis[1])
prf500.normalize(mode='peak')

prior250=xid_mod.prior(prf250,im250,nim250,w_250,im250phdu)
prior250.prior_cat(inra,indec,prior_cat)
prior250.prior_bkg(0,2)
prior350=xid_mod.prior(prf350,im350,nim350,w_350,im350phdu)
prior350.prior_cat(inra,indec,prior_cat)
prior350.prior_bkg(0,2)
prior500=xid_mod.prior(prf500,im500,nim500,w_500,im500phdu)
prior500.prior_cat(inra,indec,prior_cat)
prior500.prior_bkg(0,2)

thdulist,prior250,prior350,prior500,posterior=xid_mod.fit_SPIRE(prior250,prior350,prior500)
output_folder='/Users/jillianscudder/XID_plus/Output/'
thdulist.writeto(output_folder+'XIDp_ALMA_SPIRE_beta_'+field+'_dat.fits')
outfile=output_folder+'XIDp_SPIRE_beta_test.pkl'
with open(outfile, 'wb') as f:
    pickle.dump({'psw':prior250,'pmw':prior350,'plw':prior500, 'post':posterior},f)

