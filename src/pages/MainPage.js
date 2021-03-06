import React, { Component } from 'react';
import { Switch, Icon, InputGroup, Button, Tooltip, Callout, Toaster, Card, Dialog, FormGroup, NumericInput, Collapse } from '@blueprintjs/core';
import ls from 'local-storage'
import Download from '@axetroy/react-download';
import DragAndDropFileUpload from '../components/DragAndDropFileUpload'

const toast = Toaster.create({
    className: "main",
    position: "top",
});

const cardListStyles = {
    display: "flex",
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "center",
}
  
const cardStyles = {
    maxWidth: "25%",
    minWidth: "230px",
    minHeight: "200px",
    flex: "1",
    margin: "5px",
}

class MainPage extends Component {
    constructor(props) {
        super()
        this.state = {
            username: "",
            password: "",
            loggingIn: false,
            showPassword: false,
            connectionSuccessful: false,
            connectionErrorMessage: undefined,
            persons: [],
            newMember_firstname: undefined,
            newMember_lastname: undefined,
            newMember_initials: undefined,
            newMember_roomy: true,
            newMember_noseats: 4
        }
    }

    componentDidMount() {
        this.setState({
            username: ls.get("username") || "",
            persons: ls.get("persons") || [],
        })
    }

    render() {
        return (
            <div className="bp3-dark main-form">
                <br/>
                <center><h2>Carpool Party</h2></center>
                {this.getWebuntisFieldset()}
                <br/>
                {this.getCarpoolMembersFieldset()}
                <br/>
                {this.getDrivingPlanFieldset()}
            </div>
        );
    }

    /*****************************************************
     * MAIN SECTIONS
     *****************************************************/

    getWebuntisFieldset() {
        const lockButton = (
            <Tooltip content={`${this.state.showPassword ? "Hide" : "Show"} Password`}>
                <Button
                    style={{ color: "orange" }}
                    icon={this.state.showPassword ? "unlock" : "lock"}
                    intent="warning"
                    minimal={true}
                    onClick={() => this.setState({showPassword: !this.state.showPassword})} />
            </Tooltip>
            );
        return (
            <fieldset className="main-form" style={{ padding : "20px" }}>
                {this.getWebUntisLegend()}
                <div className="login-form">
                    <Collapse isOpen={!this.state.webuntisCollapsed} >
                        <Callout intent="primary" icon="info-sign">Please enter your initials and password:</Callout>
                        <InputGroup
                            style={{ width: "300px" }}
                            value={this.state.username}
                            id="username"
                            placeholder="Enter your username (initials)..."
                            onChange={(e) => this.updateState("username", e.target.value)} />
                        <InputGroup
                            style={{ width: "300px" }}
                            value={this.state.password}
                            id="password"
                            rightElement={lockButton}
                            placeholder="Enter your password..."
                            type={this.state.showPassword ? "text" : "password"}
                            onChange={(e) => this.setState({ password: e.target.value})}
                            />
                        <Button
                            type="submit"
                            fill={true}
                            icon="signal-search"
                            loading={this.state.loggingIn}
                            text="Test Connection"
                            disabled={this.disableConnectionButton()}
                            intent="primary"
                            onClick={() => {
                                this.testWebUntisConnection()
                            }}
                            />
                        { !this.state.connectionSuccessful && this.state.connectionErrorMessage
                            ? 
                            <Callout intent="danger" icon="error">{this.state.connectionErrorMessage}</Callout>
                            : 
                            null
                        }
                    </Collapse>
                    <Collapse isOpen={this.state.webuntisCollapsed} >
                        {this.state.connectionSuccessful ? <Callout intent="success" icon="tick">Connection successfully tested</Callout> : null }
                    </Collapse>
                </div>
            </fieldset>
        )
    }

    getCarpoolMembersFieldset() {
        return (
            <fieldset style={cardListStyles}>
                {this.getCarpoolMembersLegend()}
                <Collapse isOpen={!this.state.carpoolmembersCollapsed} >
                    <center>
                        <DragAndDropFileUpload onDrop={(files) => {
                                let reader = new FileReader();
                                reader.onloadend = (e) => {
                                    let persons = JSON.parse(e.target.result);
                                    this.updateState("persons", persons)
                                }
                                reader.readAsText(files[0]);
                            }}
                        />
                    </center>
                    <div style={cardListStyles}>
                        {this.state.persons.map((person) => {
                            return (this.createCard(person))
                        })}
                        <Button 
                            style={cardStyles}
                            icon="add"
                            minimal={true}
                            intent="primary"
                            onClick={() => this.openDialogForNewPerson()}
                            />
                    </div>
                    {this.getPersonDetailsDialog()}
                    <br/>
                    <center>
                        <Download file={"carpool-party-members.json"} content={JSON.stringify(this.state.persons, null, 2)}>
                            <Button icon="download" text="Save to file" style={{float: "right"}} minimal={true} />
                        </Download>
                    </center>
                </Collapse>
                <Collapse isOpen={this.state.carpoolmembersCollapsed} >
                    <center>
                        <Callout style={{ width: "300px" }} intent="success" icon="tick">{this.state.persons.length} members for your carpool party!</Callout>
                    </center>
                </Collapse>
            </fieldset>
        )
    }

    getDrivingPlanFieldset() {
        return (
            <fieldset style={cardListStyles}>
                {this.getDrivingPlanLegend()}
                <center>
                    { (this.state.drivingPlan === undefined)
                    ? 
                        <div>
                            <Button 
                                text="Calculate Driving Plan"
                                icon="send-to-map"
                                intent="primary"
                                disabled={this.disableConnectionButton()}
                                loading={this.state.waitingForPlan}
                                style={{
                                    width:  "200px",
                                    height: "100px"
                                }}
                                onClick={() => this.requestDrivingPlan()}
                                />
                            {this.disableConnectionButton()
                            ?
                                <Callout
                                intent="primary"
                                icon="info-sign"
                                style={{width:  "200px"}}>
                                    Username and password are missing.
                                </Callout>
                            :
                                null
                            }
                        </div>
                     :
                        // display driving plan
                        this.state.drivingPlan.summary
                    }                    
                </center>
            </fieldset>
        )
    }

    /*****************************************************
     * SECTION ROUTINES
     *****************************************************/

    getPersonDetailsDialog() {
        return (
            <Dialog 
                className=""
                icon="person"
                autoFocus={true}
                title="New Carpool Party member"
                onClose={() => {this.setState({isDialogOpen: false})}}
                isOpen={this.state.isDialogOpen}
                >
                
                <FormGroup
                    helperText={undefined}
                    label="First Name"
                    labelFor="input-first-name"
                    labelInfo={undefined} >
                    <InputGroup 
                        id="input-first-name"
                        placeholder="John"
                        autoComplete="off"
                        autoFocus={true}
                        value={this.state.newMember_firstname}
                        onKeyPress={(e) => this.handleKeyPress(e)}
                        onChange={(e) => { this.setState({newMember_firstname: e.target.value}) }} />
                </FormGroup>
                <FormGroup
                    helperText={undefined}
                    label="Last Name"
                    labelFor="input-last-name"
                    labelInfo={undefined} >
                    <InputGroup 
                        id="input-last-name"
                        placeholder="Doe"
                        autoComplete="off"
                        value={this.state.newMember_lastname}
                        onKeyPress={(e) => this.handleKeyPress(e)}
                        onChange={(e) => { this.setState({newMember_lastname: e.target.value}) }} />
                </FormGroup>
                <FormGroup
                    helperText={undefined}
                    label="Initials"
                    labelFor="input-initials"
                    labelInfo="(must be unique)" >
                    <InputGroup 
                        id="input-initials"
                        placeholder="Jd"
                        autoComplete="off"
                        value={this.state.newMember_initials}
                        onKeyPress={(e) => this.handleKeyPress(e)}
                        onChange={(e) => { this.setState({newMember_initials: e.target.value}) }} />
                </FormGroup>
                <FormGroup
                    helperText={undefined}
                    label="Number of Seats"
                    labelFor="input-noseats"
                    labelInfo={undefined} >
                    <NumericInput 
                        id="input-noseats"
                        value={this.state.newMember_noseats}
                        leftIcon="person"
                        min={2}
                        max={10}
                        onKeyPress={(e) => this.handleKeyPress(e)}
                        onValueChange={(number, string) => { this.setState({newMember_noseats: number}) }} />
                </FormGroup>
                <FormGroup
                    helperText={undefined}
                    label="Roomy car"
                    labelFor="input-roomy"
                    labelInfo={undefined} >
                    <Switch 
                        id="input-roomy"
                        large={true}
                        checked={this.state.newMember_roomy}
                        onKeyPress={(e) => this.handleKeyPress(e)}
                        onChange={(e) => {
                                console.log(this.state.newMember_roomy + " --> " + !this.state.newMember_roomy)
                                this.setState({newMember_roomy: !this.state.newMember_roomy})
                             }} />
                </FormGroup>
                <center>
                    <Button
                        style={{width: "100px" }}
                        icon="delete"
                        text="Cancel"
                        onClick={() => this.setState({
                            isDialogOpen: false
                            })}/>
                    {this.state.memberBeingModified
                      ? 
                      <Button
                        style={{width: "100px" }}
                        icon="floppy-disk"
                        text="Save"
                        type="submit"
                        intent="primary"
                        disabled={this.disableAddPersonDialog()}
                        onClick={() => this.handleModifyPersonSubmit()}/>
                      :
                      <Button
                        style={{width: "100px" }}
                        icon="add"
                        text="Add"
                        type="submit"
                        intent="primary"
                        disabled={this.disableAddPersonDialog()}
                        onClick={() => this.handleNewPersonSubmit()}/>
                    }
                </center>
                
            </Dialog>
        )
    }

    getWebUntisLegend() {
        let btnCaret = this.state.webuntisCollapsed ? "caret-down" : "caret-up"
        return (
            <legend style={{ padding: "5px 10px 5px 10px"}}>
                WebUntis connection
                &nbsp;&nbsp;
                <Icon icon={btnCaret} onClick={() => this.setState({ webuntisCollapsed: !this.state.webuntisCollapsed })} />
            </legend>
        )
    }

    getCarpoolMembersLegend() {
        let btnCaret = this.state.carpoolmembersCollapsed ? "caret-down" : "caret-up"
        return (
            <legend style={{ padding: "5px 10px 5px 10px" }}>
                Add Carpool Party Members
                &nbsp;&nbsp;
                <Icon icon={btnCaret} onClick={() => this.setState({ carpoolmembersCollapsed: !this.state.carpoolmembersCollapsed })} />
            </legend>
        )
    }

    getDrivingPlanLegend() {
        return (
            <legend style={{ padding: "5px 10px 5px 10px" }}>
                Carpool Party Driving Plan
            </legend>
        )
    }

    createCard(person) {
        //firstName, lastName, initials, carSize, numberOfSeats
        return (
            <Card 
                key={person.initials}
                interactive={true}
                elevation="zero"
                onClick={() => this.openDialogForExistingPerson(person.initials)}
                style={cardStyles} >
                <div style={{ float: "right"}}>
                    <Button icon="delete" minimal={true} onClick={(e) => {this.deletePerson(e, person.initials)}} />
                </div>
                <h2>{person.firstName} {person.lastName}</h2>
                <ul>
                    <li><b>Initials: </b> {person.initials}</li>
                    <li><b>Number of Seats: </b> {person.numberOfSeats}</li>
                    <li><b>Car Type: </b> {person.isCarRoomy ? "roomy" : "small"}</li>
                </ul>
            </Card>
        )
    }

    /*****************************************************
     * HANDLERS
     *****************************************************/ 
    
    async testWebUntisConnection() {
        this.setState( { loggingIn: true })
        await this.login("checkConnection", false)
        this.setState({ loggingIn: false})
    }
    
    async requestDrivingPlan() {
        this.setState( { waitingForPlan: true, carpoolmembersCollapsed: true })
        await this.login("login", true)
        await this.calculatePlan()
        this.logout()
        this.setState( { waitingForPlan: false })
    }

    newPersonDataInvalid() {
        console.log(this.state)
        let fnOk = this.state.newMember_firstname
        let lnOk = this.state.newMember_lastname
        let inOk = this.state.newMember_initials
        let dataInvalid = (fnOk && lnOk && inOk) !== true
        if (dataInvalid) {
            return true
        } else {
            return false
        }        
    }

    getPersonByInitials(initials) {
        for (let i=0; i < this.state.persons.length; i++) {
            let person = this.state.persons[i]
            if (person.initials === initials) {
                return person
            }
        }
        return null
    }

    handleModifyPersonSubmit() {
        if (this.state.memberBeingModified !== this.state.newMember_initials) {
            // the initials have changed, need to check for duplicates
            let person = this.getPersonByInitials(this.state.newMember_initials)
            if (person !== null) {
                let msg = "You cannot add another member with the same initials as " + person.firstName + " " + person.lastName + "(" + person.initials + ")"
                toast.show({message: msg, intent: "danger", icon: "error"})
                return
            }
        }
        // modify member
        let persons = []
        for (let i=0; i < this.state.persons.length; i++) {
            let person = this.state.persons[i]
            if (person.initials === this.state.memberBeingModified) {
                person.firstName = this.state.newMember_firstname
                person.lastName = this.state.newMember_lastname
                person.initials = this.state.newMember_initials
                person.numberOfSeats = this.state.newMember_noseats
                person.isCarRoomy = this.state.newMember_roomy
            }
            persons.push(person)
        }
        this.updateState("persons", persons)
        this.setState({ isDialogOpen: false })
    }

    handleNewPersonSubmit() {
        // check if any existing person has the same initials
        let person = this.getPersonByInitials(this.state.newMember_initials)
        if (person !== null) {
            let msg = "You cannot add another member with the same initials as " + person.firstName + " " + person.lastName + "(" + person.initials + ")"
            toast.show({message: msg, intent: "danger", icon: "error"})
            return
        } else {
            // add new member
            let persons = this.state.persons
            person = {}
            person.firstName = this.state.newMember_firstname
            person.lastName = this.state.newMember_lastname
            person.initials = this.state.newMember_initials
            person.numberOfSeats = this.state.newMember_noseats
            person.isCarRoomy = this.state.newMember_roomy
            persons.push(person)
            this.updateState("persons", persons)
            this.setState({ isDialogOpen: false })
        }
    }

    handleKeyPress = (event) => {
        if (event.key === 'Enter' && !this.disableAddPersonDialog()) {
            if (this.state.memberBeingModified) {
                this.handleModifyPersonSubmit()
            } else {
                this.handleNewPersonSubmit()
            }
        }
    }

    disableAddPersonDialog() {
        return (
               (this.state.newMember_firstname == null || this.state.newMember_firstname === '')
            || (this.state.newMember_lastname == null || this.state.newMember_lastname === '')
            || (this.state.newMember_initials == null || this.state.newMember_initials === '')
        )
    }

    disableConnectionButton() {
        return (
               (this.state.username == null || this.state.username === '')
            || (this.state.password == null || this.state.password === '')
        )
    }

    deletePerson(e, initials) {
        let persons = this.state.persons
        let index
        for (let i=0; i < persons.length; i++) {
            let person = persons[i]
            if (person.initials === initials) {
                index = i
                break
            }
        }
        persons.splice(index, 1)
        this.updateState("persons", persons)
        e.stopPropagation()
    }

    openDialogForNewPerson() {
        this.setState({
            isDialogOpen: true,
            memberBeingModified: undefined,
            newMember_firstname: "",
            newMember_lastname: "",
            newMember_initials: "",
            newMember_roomy: true,
            newMember_noseats: 5,
        })
    }

    openDialogForExistingPerson(initials) {
        const person = this.getPersonByInitials(initials)
        if (person) {
            this.setState({
                isDialogOpen: true,
                memberBeingModified: initials,
                newMember_firstname: person.firstName,
                newMember_lastname: person.lastName,
                newMember_initials: person.initials,
                newMember_roomy: person.isCarRoomy,
                newMember_noseats: person.numberOfSeats,
            })
        }
    }

    /*****************************************************
     * REQUESTS TO BACKEND
     *****************************************************/ 

    async calculatePlan() {
        try {
            await fetch('http://desolate-stream-81085.herokuapp.com:80/calculatePlan', {
                method: 'POST',
                headers: {
                    'Content-Type' : 'application/json'
                },
                body: JSON.stringify(this.state.persons)
            })
            .then(response => {
                if (response.ok) {
                    // request succeeded
                    toast.show({message: "Successfully calculated a driving plan", intent: "success", icon: "tick"})
                    response.json().then(drivingPlan => {
                        this.setState( { drivingPlan })
                        console.log(drivingPlan)
                    })
                } else {
                    // request failed -> return object's message will contain details
                    try {
                        response.json().then(pkg => {
                            const msg = "Calculation of Driving Plan failed: " + pkg.message
                            toast.show({message: msg, intent: "danger", icon: "error"})
                        })
                    } catch (exception) {
                        console.log("caught")
                    }
                }
            })
            .catch(error => {
                // connection failed (no connection or exception on server)
                const msg = "Calculation of Driving Plan failed: " + error
                toast.show({message: msg, intent: "danger", icon: "error"})
            })
        } catch {
            console.log("sasdfa")
        }
    }

    logout() {
        // can run in background, no need to wait for reply
        fetch('http://desolate-stream-81085.herokuapp.com:80/logout', { method: 'POST' })
    }

    async login(route, quiet) {
        await fetch('http://desolate-stream-81085.herokuapp.com:80/' + route, {
            method: 'POST',
            headers: {
                'Content-Type' : 'application/json'
            },
            body: JSON.stringify({ username: this.state.username, hash: Buffer.from(this.state.password).toString('base64')})
        })
        .then(response => {
            if (response.ok) {
                // connection succeeded
                if (!quiet) {
                    toast.show({message: "Successfully connected to WebUntis with user " + this.state.username, intent: "success", icon: "tick"})
                }
                this.setState( { connectionSuccessful: true, webuntisCollapsed: true })
            } else {
                // connection failed -> return object's message will contain details
                response.json().then(pkg => {
                    const msg = "Connection failed: " + pkg.message
                    if (!quiet) {
                        toast.show({message: msg, intent: "danger", icon: "error"})
                    }
                    this.setState({ connectionErrorMessage: msg})
                })
            }
        })
        .catch(error => {
            // connection failed (no connection or exception on server)
            const msg = "An error failed: " + error
            if (!quiet) {
                toast.show({message: msg, intent: "danger", icon: "error"})
            }
            this.setState({ connectionErrorMessage: msg })
        })
    }
    
    /*****************************************************
     * UTILITY FUNCTIONS
     *****************************************************/ 
    
    updateState(name, value) {
        ls.set(name, value);
        this.setState({[name]: value})
    }

}

export default MainPage;
