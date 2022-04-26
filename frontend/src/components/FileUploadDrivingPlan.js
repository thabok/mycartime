import React from 'react';
import {useDropzone} from 'react-dropzone';
import {Callout} from '@blueprintjs/core';


function FileUploadDrivingPlan(onDrop) {

    const {getRootProps, getInputProps, isDragActive} = useDropzone(onDrop)
    let inputProps = getInputProps()
    inputProps['accept'] = ".json";

    return (
      <div {...getRootProps()} style={{ "width" : 500}}>
        <input {...inputProps} />
        <Callout intent="primary" title="Load existing driving-plan" icon="info-sign">
        {
          isDragActive
          ?
            <p>Drop the json file here to load the stored state.</p>
          :
            <p>You can load a driving plan (*.json) that you previously exported.</p> 
        }
        </Callout>
      </div>
    )
}

export default FileUploadDrivingPlan;