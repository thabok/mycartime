import Download from '@axetroy/react-download';
import { Button, Callout, Card, Checkbox, Collapse, Dialog, FormGroup, Icon, InputGroup, NumericInput, ProgressBar, Radio, RadioGroup, Switch, Toaster, Tooltip } from '@blueprintjs/core';
import { DateInput } from '@blueprintjs/datetime';
import ls from 'local-storage';
import React, { Component } from 'react';
import DragAndDropFileUpload from '../components/DragAndDropFileUpload';
import FileUploadDrivingPlan from '../components/FileUploadDrivingPlan';
import DrivingPlan from './DrivingPlan';

const dayNumbersA = [ 0, 1, 2, 3, 4]
const dayNumbersB = [ 5, 6, 7, 8, 9]

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
    position: "relative",
}

class MainPage extends Component {
    constructor(props) {
        super(props)
        this.state = {
            backendService: "java",
            username: "",
            password: "",
            loggingIn: false,
            showPassword: false,
            connectionSuccessful: false,
            connectionErrorMessage: undefined,
            persons: [],
            drivingPlan: undefined,
            newMember_firstname: undefined,
            newMember_lastname: undefined,
            newMember_initials: undefined,
            newMember_noseats: 5,
            newMember_customDays: this.getEmptyCustomDaysMap(),
            newMember_isPartTime: false,
            progressValue: 0,
            progressMessage: "",
            showAdvancedOptions: false
        }
        this.timer = null
    }

    componentWillUnmount() {
        this.stopProgressTimer()
    }
    
    componentDidMount() {
        this.setState({
            username: ls.get("username") || "",
            persons: ls.get("persons") || [],
            drivingPlan: ls.get("drivingPlan") || undefined,
            ABWeekStartDate: new Date(ls.get("ABWeekStartDate")) || new Date(),
        })
    }

    render() {
        return (
            <div className="bp3-dark main-form">
                <br/>
                <center><h2>Carpool Party</h2></center>
                {/* {this.getBackendPicker()}
                <br/> */}
                {this.getWebuntisFieldset()}
                <br/>
                {this.getCarpoolMembersFieldset()}
                <br/>
                {this.getDrivingPlanFieldset()}
                <br/><br/>
            </div>
        );
    }

    /*****************************************************
     * MAIN SECTIONS
     *****************************************************/

    getBackendPicker() {
        return (
            <fieldset className="main-form" style={{ padding: "20px" }}>
                <legend style={{ padding: "5px 10px 5px 10px" }}>Backend</legend>
                <div style={{ textAlign: "center" }}>
                    <FormGroup inline={true} style={{ display: "inline-block" }}>
                        <RadioGroup
                            onChange={(e) => this.updateState("backendService", e.target.value)}
                            selectedValue={this.state.backendService || "java"}
                            inline={true}
                        >
                            <Radio label="Java" value="java" />
                            <Radio label="Python" value="python" />
                        </RadioGroup>
                    </FormGroup>
                </div>
            </fieldset>
        );
    }

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
                        <br/>
                        <Callout intent="primary" icon="info-sign">
                        WebUntis only allows to query the schedule for specific dates. Please select a Monday to indicate a 2-weeks period (A week + B week):
                        </Callout>
                        <DateInput
                            value={this.state.ABWeekStartDate}
                            onChange={(selectedDate, isUserChange) => {
                                if (selectedDate && selectedDate.getDay() === 1) {
                                    this.updateState("ABWeekStartDate", selectedDate)
                                } else {
                                    toast.show({message: "Please select a Monday.", intent: "danger", icon: "error"})
                                }
                            }}
                            fill={true}
                            formatDate={date => date.toLocaleDateString()}
                            parseDate={str => new Date(str)}
                            highlightCurrentDay={true}
                            minDate={this.getMinDate()}
                            maxDate={this.getMaxDate()}
                            placeholder="dd.mm.yyyy" />
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
                            icon="graph-remove"
                            minimal={true}
                            intent="danger"
                            onClick={() => this.clearCustomPrefs()}
                            />
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
                        <Callout style={{ width: "300px" }} intent="success" icon="tick">You have {this.state.persons.length} members in your carpool party!</Callout>
                    </center>
                </Collapse>
            </fieldset>
        )
    }

    getMinDate() {
        const today = new Date()
        let minDate = today
        minDate.setFullYear(today.getFullYear() - 1)
        return minDate
    }
    
    getMaxDate() {
        const today = new Date()
        let minDate = today
        minDate.setFullYear(today.getFullYear() + 1)
        return minDate
    }

    getDrivingPlanFieldset() {
        return (
            <fieldset style={cardListStyles}>
                {this.getDrivingPlanLegend()}
                {
                    typeof this.state.drivingPlan !== typeof {}
                ? 
                    this.getDrivingPlanButton()
                :
                    <div>
                        <DrivingPlan plan={this.state.drivingPlan} updatePlan={(plan) => this.updateState("drivingPlan", plan)}/>
                        <div style={{"width":"950px"}}>
                            <Download file={"driving-plan.json"} content={JSON.stringify(this.state.drivingPlan, null, 2)}>
                                <Button icon="download" text="Save to file" style={{float: "right"}} minimal={true} />
                            </Download>
                        </div>
                    </div>
                }           
            </fieldset>
        )
    }

    getDrivingPlanButton() {
        return (
            <div>
                <center>
                    <Button 
                        text="Calculate Driving Plan"
                        icon="send-to-map"
                        intent="primary"
                        disabled={this.disableConnectionButton() || (this.state.ABWeekStartDate == null || this.state.ABWeekStartDate === '')}
                        loading={this.state.waitingForPlan}
                        style={{
                            width:  "200px",
                            height: "100px"
                        }}
                        onClick={() => this.requestDrivingPlan()}
                    />
                </center>
                <br/>
                <FileUploadDrivingPlan onDrop={(files) => {
                        let reader = new FileReader();
                        reader.onloadend = (e) => {
                            let drivingPlan = JSON.parse(e.target.result);
                            this.updateState("drivingPlan", drivingPlan)
                        }
                        reader.readAsText(files[0]);
                    }}
                />
                {/* Configure Progress Popover */}
                {this.getProgressDialog()}
                {/* Disable button if credentials are missing */}
                {this.disableConnectionButton()
                ?
                    <Callout
                    intent="primary"
                    icon="info-sign"
                    style={{width:  "200px"}}>
                        Username / password / start date are missing (see WebUntis section on top)
                    </Callout>
                :
                    null
                }
            </div>
        )
    }

    /*****************************************************
     * SECTION ROUTINES
     *****************************************************/

    getProgressDialog() {
        return (
            <Dialog 
            className=""
            icon="person"
            autoFocus={true}
            title="Calculating plan..."
            onClose={() => {this.setState({isDialogOpen: false})}}
            isOpen={this.state.waitingForPlan && this.state.isProgressDialogOpen}>
                <ProgressBar
                    intent="primary"
                    value={this.state.progressValue}
                    />
                <center>
                    <br/>
                    {this.state.progressMessage}
                    <br/><br/>
                    <Button
                        style={{width: "100px"}}
                        icon="delete"
                        text="Cancel"
                        intent="danger"
                        onClick={() => this.cancelCalculation()}/>
                </center>
            </Dialog>)
    }

    isChecked_CustomDays(dayNumber, propertyName) {
        const value = this.getCustomDayValue(dayNumber, propertyName)
        if (value !== null) {
            return value
        } else {
            return false
        }
    }

    getCustomDayValue(dayNumber, propertyName) {
        if (this.state.newMember_customDays !== undefined) {
            return this.state.newMember_customDays[dayNumber][propertyName]
        } else {
            return null;
        }
    }

    updateCustomDays(dayNumber, propertyName, value) {
        // for null value -> assume flag and invert the current state (=toggle)
        let newValue = value
        if (newValue === null) {
            newValue = !this.isChecked_CustomDays(dayNumber, propertyName)
        }

        let map = this.state.newMember_customDays
        map[dayNumber][propertyName] = newValue
        // handle dependencies between needsCar, drivingSkip, skipMorning and skipAfternoon
        switch(propertyName) {
            case "ignoreCompletely":
                // also disable needsCar/skipMorning/skipAfternoon
                map[dayNumber]['needsCar'] = newValue
                map[dayNumber]['skipMorning'] = newValue
                map[dayNumber]['skipAfternoon'] = newValue
                break
            case "needsCar":
                if (newValue === false) {
                    // also disable skipMorning/skipAfternoon
                    map[dayNumber]['skipMorning'] = false
                    map[dayNumber]['skipAfternoon'] = false
                } else {
                    // disable drivingSkip
                    map[dayNumber]['drivingSkip'] = false
                }
                break
            case "drivingSkip":
                if (newValue === true) {
                    // disable needsCar
                    map[dayNumber]['needsCar'] = false
                    map[dayNumber]['skipMorning'] = false
                    map[dayNumber]['skipAfternoon'] = false
                }
                break
            case "skipMorning":
            case "skipAfternoon":
                if (newValue === true) {
                    // also enable "needsCar"
                    map[dayNumber]['needsCar'] = true
                    // disable drivingSkip
                    map[dayNumber]['drivingSkip'] = false
                }
                break
            case "noWaitingAfternoon":
                map[dayNumber]['noWaitingAfternoon'] = newValue
                break
            default:
                break
        }
        this.setState( { newMember_customDays: map } )
    }

    getPersonDetailsDialog() {
        return (
            <Dialog 
                className=""
                style={{ width: "1000px", padding: "10px" }}
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
                    label="Part-time"
                    labelFor="input-part-time"
                    labelInfo="Do they work part time? (e.g. Reffi)" >
                    <Switch 
                        id="input-part-time"
                        checked={this.state.newMember_isPartTime}
                        onChange={(e) => this.setState( { newMember_isPartTime: !this.state.newMember_isPartTime } )}/>
                </FormGroup>
                <FormGroup
                    helperText={undefined}
                    label="Number of Seats"
                    labelFor="input-noseats"
                    labelInfo={undefined} >
                    <NumericInput 
                        id="input-noseats"
                        value={this.state.newMember_noseats}
                        leftIcon="drive-time"
                        min={1}
                        max={10}
                        onKeyPress={(e) => this.handleKeyPress(e)}
                        onValueChange={(number, string) => { this.setState({newMember_noseats: number}) }} />
                </FormGroup>
                
                <div>
                    <Switch 
                        id="switch-advanced"
                        large={true}
                        style={{ float: "right"}}
                        innerLabel={this.state.showAdvancedOptions ? "Hide Advanced Options" : "Show Advanced Options"}
                        checked={this.state.showAdvancedOptions}
                        onChange={(e) => this.setState( { showAdvancedOptions: !this.state.showAdvancedOptions } )}/>
                </div>
                { this.state.showAdvancedOptions ?
                    <div>
                        <hr/>
                        <FormGroup
                            helperText={undefined}
                            label="Customize preferences for specific days"
                            labelFor="lonely-driver">
                            <table border="1">
                                <thead>
                                    <tr><th><Button
                                        icon="delete"
                                        text="Reset"
                                        intent="danger"
                                        onClick={() => this.setState({ newMember_customDays: this.getEmptyCustomDaysMap() })}/>
                                        </th>
                                        <th>Mon</th><th>Tue</th><th>Wed</th><th>Thu</th><th>Fri</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr>
                                        <td><b>Week A</b></td>
                                        {dayNumbersA.map((dayNumber) => {
                                            return (
                                        <td key={dayNumber}>
                                            <Checkbox checked={this.state.newMember_customDays[dayNumber].ignoreCompletely} onChange={() => this.updateCustomDays(dayNumber, 'ignoreCompletely', null)} label="Ignore completely" />
                                            <Checkbox disabled={this.isChecked_CustomDays(dayNumber, 'ignoreCompletely')} checked={this.state.newMember_customDays[dayNumber].needsCar} onChange={() => this.updateCustomDays(dayNumber, 'needsCar', null)} label="Needs car" />
                                            <Checkbox disabled={this.isChecked_CustomDays(dayNumber, 'ignoreCompletely')} checked={this.state.newMember_customDays[dayNumber].drivingSkip} onChange={() => this.updateCustomDays(dayNumber, 'drivingSkip', null)} label="Doesn't want to drive" />
                                            <Checkbox disabled={this.isChecked_CustomDays(dayNumber, ['ignoreCompletely', 'drivingSkip'])} checked={this.state.newMember_customDays[dayNumber].skipMorning} onChange={() => this.updateCustomDays(dayNumber, 'skipMorning', null)} label="Skip on morning" />
                                            <Checkbox disabled={this.isChecked_CustomDays(dayNumber, ['ignoreCompletely', 'drivingSkip'])} checked={this.state.newMember_customDays[dayNumber].skipAfternoon} onChange={() => this.updateCustomDays(dayNumber, 'skipAfternoon', null)} label="Skip on afternoon" />
                                            <Checkbox disabled={this.isChecked_CustomDays(dayNumber, 'noWaitingAfternoon')} checked={this.state.newMember_customDays[dayNumber].noWaitingAfternoon} onChange={() => this.updateCustomDays(dayNumber, 'noWaitingAfternoon', null)} label="No waiting on afternoon" />
                                            <InputGroup placeholder="start time: 7:40" disabled={this.isChecked_CustomDays(dayNumber, 'ignoreCompletely')} value={this.state.newMember_customDays[dayNumber].customStart} onChange={(e) => this.updateCustomDays(dayNumber, 'customStart', e.target.value)} />
                                            <InputGroup placeholder="end time: 14:30" disabled={this.isChecked_CustomDays(dayNumber, 'ignoreCompletely')} value={this.state.newMember_customDays[dayNumber].customEnd} onChange={(e) => this.updateCustomDays(dayNumber, 'customEnd', e.target.value)} />
                                        </td>)
                                        })}
                                    </tr>
                                    <tr>
                                        <td><b>Week B</b></td>
                                        {dayNumbersB.map((dayNumber) => {
                                            return (
                                            <td key={dayNumber}>
                                                <Checkbox checked={this.state.newMember_customDays[dayNumber].ignoreCompletely} onChange={() => this.updateCustomDays(dayNumber, 'ignoreCompletely', null)} label="Ignore completely" />
                                                <Checkbox disabled={this.isChecked_CustomDays(dayNumber, 'ignoreCompletely')} checked={this.state.newMember_customDays[dayNumber].needsCar} onChange={() => this.updateCustomDays(dayNumber, 'needsCar', null)} label="Needs car" />
                                                <Checkbox disabled={this.isChecked_CustomDays(dayNumber, 'ignoreCompletely')} checked={this.state.newMember_customDays[dayNumber].drivingSkip} onChange={() => this.updateCustomDays(dayNumber, 'drivingSkip', null)} label="Doesn't want to drive" />
                                                <Checkbox disabled={this.isChecked_CustomDays(dayNumber, ['ignoreCompletely', 'drivingSkip'])} checked={this.state.newMember_customDays[dayNumber].skipMorning} onChange={() => this.updateCustomDays(dayNumber, 'skipMorning', null)} label="Skip on morning" />
                                                <Checkbox disabled={this.isChecked_CustomDays(dayNumber, ['ignoreCompletely', 'drivingSkip'])} checked={this.state.newMember_customDays[dayNumber].skipAfternoon} onChange={() => this.updateCustomDays(dayNumber, 'skipAfternoon', null)} label="Skip on afternoon" />
                                                <Checkbox disabled={this.isChecked_CustomDays(dayNumber, 'noWaitingAfternoon')} checked={this.state.newMember_customDays[dayNumber].noWaitingAfternoon} onChange={() => this.updateCustomDays(dayNumber, 'noWaitingAfternoon', null)} label="No waiting on afternoon" />
                                                <InputGroup placeholder="start time: 7:40" disabled={this.isChecked_CustomDays(dayNumber, 'ignoreCompletely')} value={this.state.newMember_customDays[dayNumber].customStart} onChange={(e) => this.updateCustomDays(dayNumber, 'customStart', e.target.value)} />
                                                <InputGroup placeholder="end time: 14:30" disabled={this.isChecked_CustomDays(dayNumber, 'ignoreCompletely')} value={this.state.newMember_customDays[dayNumber].customEnd} onChange={(e) => this.updateCustomDays(dayNumber, 'customEnd', e.target.value)} />
                                            </td>)
                                            })}
                                    </tr>
                                </tbody>
                            </table>
                        </FormGroup>
                        <hr/>
                    </div>
                : null }
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
                <Icon 
                    style={{ cursor : "pointer" }}
                    icon={btnCaret}
                    onClick={() => this.setState({ webuntisCollapsed: !this.state.webuntisCollapsed })} />
            </legend>
        )
    }

    getCarpoolMembersLegend() {
        let btnCaret = this.state.carpoolmembersCollapsed ? "caret-down" : "caret-up"
        return (
            <legend style={{ padding: "5px 10px 5px 10px" }}>
                Add Carpool Party Members
                &nbsp;&nbsp;
                <Icon
                    style={{ cursor : "pointer" }}
                    icon={btnCaret}
                    onClick={() => this.setState({ carpoolmembersCollapsed: !this.state.carpoolmembersCollapsed })} />
            </legend>
        )
    }

    getDrivingPlanLegend() {
        return (
            <legend style={{ padding: "5px 10px 5px 10px" }}>
                Carpool Party Driving Plan
                &nbsp;&nbsp;
                <Button
                    minimal={true}
                    icon="trash"
                    onClick={() => this.updateState("drivingPlan", undefined)} />
                &nbsp;&nbsp;
                <Button
                    icon="random"
                    minimal={true}
                    disabled={this.disableConnectionButton() || (this.state.ABWeekStartDate == null || this.state.ABWeekStartDate === '')}
                    onClick={() => {
                        this.updateState("drivingPlan", undefined)
                        this.requestDrivingPlan()
                    }} />
                &nbsp;&nbsp;
                <Button
                    icon="repeat"
                    minimal={true}
                    disabled={(this.disableConnectionButton() || this.state.ABWeekStartDate == null || this.state.ABWeekStartDate === '')}
                    onClick={() => {
                        let preset = this.state.drivingPlan
                        this.updateState("drivingPlan", undefined)
                        this.requestDrivingPlan(preset)
                    }} />
                &nbsp;&nbsp;
                
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
                    {person.isPartTime ? <li><b>Part-time </b></li> : null}
                </ul>
                {this.doesPersonHaveCustomPrefs(person) ? <div style={{position: "absolute", right: 10, bottom: 10}}><i>*custom prefs</i></div> : null}
            </Card>
        )
    }

    startProgressTimer() {
        this.timer = setInterval(() => this.getProgress(), 1000)
        this.setState({ progressMessage: "Preparing..." })
    }

    stopProgressTimer() {
        if (this.timer != null) {
            clearInterval(this.timer)
            this.timer = null
        }
        this.setState({
            progressValue: 0,
            progressMessage: ""
        })
    }

    /*****************************************************
     * HANDLERS
     *****************************************************/ 
    
    async testWebUntisConnection() {
        this.setState( { loggingIn: true })
        await this.login("checkConnection", false)
        this.setState({ loggingIn: false})
    }
    
    async getProgress() {
        if (this.state.backendService === "java") {
            await fetch(this.getBackendUrl() + '/progress', {
                method: 'GET',
                headers: {
                    'Content-Type' : 'application/json'
                }
            })
            .then(response => {
                if (response.ok) {
                    // update progress in state
                    response.json().then(progressObj => {
                        this.setState({
                            progressValue: progressObj.value,
                            progressMessage: progressObj.message
                        })
                    })
                }
            })
            .catch(() => {
                this.stopProgressTimer()
            })
        }
    }

    async cancelCalculation() {
        if (this.state.backendService === "java") {
            fetch(this.getBackendUrl() + '/cancel', {
                method: 'POST',
                headers: {
                    'Content-Type' : 'application/json'
                }
            })
            this.setState({ 
                waitingForPlan: false,
                isProgressDialogOpen: false
            })
            this.stopProgressTimer()
        }
    }

    async requestDrivingPlan(weekDayPermutation=undefined) {
        this.startProgressTimer()
        this.setState( { waitingForPlan: true, carpoolmembersCollapsed: true, isProgressDialogOpen: true })
        await this.login("login", true)
        await this.calculatePlan(weekDayPermutation)
        this.logout()
        this.stopProgressTimer()
        this.setState( { waitingForPlan: false, isProgressDialogOpen: false })
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
                person.isPartTime = this.state.newMember_isPartTime
                person.numberOfSeats = this.state.newMember_noseats
                person.customDays = this.state.newMember_customDays
            }
            persons.push(person)
        }
        this.updateState("persons", persons)
        console.log(persons)
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
            person.isPartTime = this.state.newMember_isPartTime
            person.numberOfSeats = this.state.newMember_noseats
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

    /* Big remove button below persons */
    clearCustomPrefs() {
        let persons = this.state.persons
        for (let i=0; i < persons.length; i++) {
            let person = persons[i]
            person.customDays = undefined
        }
        this.updateState("persons", persons)
    }

    /* Big + button below persons */
    openDialogForNewPerson() {
        this.setState({
            isDialogOpen: true,
            memberBeingModified: undefined,
            newMember_firstname: "",
            newMember_lastname: "",
            newMember_initials: "",
            newMember_isPartTime: false,
            newMember_noseats: 5,
            newMember_customDays: this.getEmptyCustomDaysMap(),
        })
    }

    doesPersonHaveCustomPrefs(person) {
        if (person.customDays !== undefined && JSON.stringify(person.customDays) !== JSON.stringify(this.getEmptyCustomDaysMap())) {
            return true
        }
        return false
    }

    getEmptyCustomDaysMap() {
        let map = {}
        for (let n=0; n < 10; n++) {
            map[n] = {
                ignoreCompletely: false,
                noWaitingAfternoon: false,
                needsCar: false,
                drivingSkip: false,
                skipMorning: false,
                skipAfternoon: false,
                customStart: "",
                customEnd: "",
            }
        }
        return map
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
                newMember_isPartTime: person.isPartTime,
                newMember_noseats: person.numberOfSeats,
                newMember_customDays: person.customDays !== undefined ? person.customDays : this.getEmptyCustomDaysMap(),
            })
        }
    }

    /*****************************************************
     * REQUESTS TO BACKEND
     *****************************************************/ 

    getBackendUrl() {
        return this.state.backendService === 'java' ? "http://127.0.0.1:1337" : "http://127.0.0.1:1338"
    }

    async calculatePlan(weekDayPermutation=undefined) {
        try {
            const referenceDate = (this.state.ABWeekStartDate.getFullYear() * 10000) + ((this.state.ABWeekStartDate.getMonth() + 1) * 100) + (this.state.ABWeekStartDate.getDate())
            const payload = {
                persons: this.state.persons,
                scheduleReferenceStartDate: referenceDate,
                preset: weekDayPermutation,
                username: this.state.username,
                hash: Buffer.from(this.state.password).toString('base64')
            }
            await fetch(this.getBackendUrl() + '/calculatePlan', {
                method: 'POST',
                headers: {
                    'Content-Type' : 'application/json'
                },
                body: JSON.stringify(payload)
            })
            .then(response => {
                if (response.ok) {
                    // request succeeded
                    toast.show({message: "Successfully calculated a driving plan", intent: "success", icon: "tick"})
                    response.json().then(drivingPlan => {
                        this.updateState("drivingPlan", drivingPlan)
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
        } catch (err) {
            console.log(err)
            const msg = "Calculation of Driving Plan failed: " + err
            toast.show({message: msg, intent: "danger", icon: "error"})
        }
    }

    logout() {
        // can run in background, no need to wait for reply
        if (this.state.backendService === "java") {
            fetch(this.getBackendUrl() + '/logout', { method: 'POST' })
        }
    }

    async login(route, quiet) {
        if (this.state.backendService === "java") {
            await fetch(this.getBackendUrl() + '/' + route, {
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
