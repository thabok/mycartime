import React from 'react';
import {useDropzone} from 'react-dropzone';
import {Callout} from '@blueprintjs/core';


function DragAndDropFileUpload(onDrop) {

    const {getRootProps, getInputProps, isDragActive} = useDropzone(onDrop)
    let inputProps = getInputProps()
    inputProps['accept'] = ".json";

    return (
      <div {...getRootProps()} style={{ "width" : 500}}>
        <input {...inputProps} />
        <Callout intent="primary" title="Add members for your Carpool Party:" icon="info-sign">
        {
          isDragActive
          ?
            <p>Drop the json file here to load the stored state.<br/><br/><i>Note: This will overwrite any items you currently have configured.</i></p>
          :
            <p>You can manually add persons using the (+) button below or upload a previously saved file to continue with that. Just drag &amp; drop the *.json file here or click to browse.</p> 
        }
        </Callout>
      </div>
    )
}

export default DragAndDropFileUpload;