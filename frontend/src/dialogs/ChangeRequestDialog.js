import { Button, Dialog, FormGroup, Icon, MenuItem, Switch } from '@blueprintjs/core';
import { Suggest } from '@blueprintjs/select';
import React, { Component } from 'react';

const flowStyle1 = {
    display: "flex",
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "right",
    padding: "20px"
}
const flowStyle2 = {
    padding: "20px"
}
const flowStyle3 = {
    display: "flex",
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "center",
    padding: "20px"
}

class ChangeRequestDialog extends Component {

    constructor(props) {
        super(props);
        this.state = {
            allowDifferentTimes: false,
            targetCandidates: [],
            schoolbound: true,
            changeRequests: [],
        }
    }

    componentDidMount() {
        this.updateTargetCandidates()
    }

    getCrPassengerCandidates() {
        let candidates = []
        for (let ptIndex=0; ptIndex<this.props.dayPlan.partyTouples.length; ptIndex++) {
            const party = this.state.schoolbound ? this.props.dayPlan.partyTouples[ptIndex].partyThere : this.props.dayPlan.partyTouples[ptIndex].partyBack
            party.passengers.forEach((passenger) => {
                passenger.driverInitials = party.driver.initials
                candidates.push(passenger)
            })
        }
        return candidates
    }

    updateTargetCandidates(item, sourcePartyTime=null) {
        let candidates = []
        let spt = sourcePartyTime != null ? this.timeToString(sourcePartyTime) : this.state.sourcePartyTime
        for (let ptIndex=0; ptIndex<this.props.dayPlan.partyTouples.length; ptIndex++) {
            const party =  this.state.schoolbound ? this.props.dayPlan.partyTouples[ptIndex].partyThere : this.props.dayPlan.partyTouples[ptIndex].partyBack
            if (!this.state.allowDifferentTimes && this.timeToString(party.time) !== spt) {
                continue
            }
            if ( (item !== undefined && party.driver.initials === item.driverInitials) ||
                 (this.state.passengerToPlace !== undefined && party.driver.initials === this.state.passengerToPlace.driverInitials)) {
                continue // doesn't make sense to move someone into the exact same party
            }
            party.passengers.forEach((passenger) => {
                passenger.driverInitials = party.driver.initials
                if (item === undefined || item.initials !== passenger.initials) {
                    candidates.push(passenger)
                }
            })
            candidates.push(party.driver)
        }
        this.setState({targetCandidates: candidates})
    }

    calculateSourcePartyTime(passengerToPlace) {
        let time = null
        for (let ptIndex=0; ptIndex<this.props.dayPlan.partyTouples.length; ptIndex++) {
            const party = this.state.schoolbound ? this.props.dayPlan.partyTouples[ptIndex].partyThere : this.props.dayPlan.partyTouples[ptIndex].partyBack
            if (party.driver.initials === passengerToPlace.initials) {
                time = party.time
            } else {
                for (let passengerIndex=0; passengerIndex<party.passengers.length; passengerIndex++) {
                    if (party.passengers[passengerIndex].initials === passengerToPlace.initials) {
                        time = party.time
                        break
                    }
                }
            }
        }
        this.setState({sourcePartyTime: this.timeToString(time)})
        return time
    }

    calculateTargetPartyTime(personToJoin) {
        let time = null
        for (let ptIndex=0; ptIndex<this.props.dayPlan.partyTouples.length; ptIndex++) {
            const party = this.state.schoolbound ? this.props.dayPlan.partyTouples[ptIndex].partyThere : this.props.dayPlan.partyTouples[ptIndex].partyBack
            if (party.driver.initials === personToJoin.initials) {
                time = party.time
            } else {
                for (let passengerIndex=0; passengerIndex<party.passengers.length; passengerIndex++) {
                    if (party.passengers[passengerIndex].initials === personToJoin.initials) {
                        time = party.time
                        break
                    }
                }
            }
        }
        this.setState({targetPartyTime: this.timeToString(time)})
    }

    renderItems = (item, { handleClick, modifiers }) => {
        if (!modifiers.matchesPredicate) {
            return null;
        }
        return <MenuItem
                    active={modifiers.active}
                    key={item.initials}
                    label={item.initials || ""}
                    text={item.firstName + " " + item.lastName || ""}
                    onClick={handleClick} />
    }

    filterItems(query, item) {
        return item.firstName.toLowerCase().indexOf(query.toLowerCase()) >= 0 
            || item.lastName.toLowerCase().indexOf(query.toLowerCase()) >= 0 
            || item.initials.toLowerCase().indexOf(query.toLowerCase()) >= 0
    }

    render() {
        return (
            <Dialog 
                className=""
                style={{ width: "1000px" }}
                icon="swap-horizontal"
                autoFocus={true}
                title={"Modify Day Plan (" + this.props.dayPlan.dayOfWeekABCombo.dayOfWeek + " " + (this.props.dayPlan.dayOfWeekABCombo.isWeekA ? " A)" : " B)")}
                onClose={() => this.props.closeCrDialog()}
                isOpen={this.props.crDialogOpen}
                >
                <div style={flowStyle1} >
                    <Switch 
                        id="switch-matching-times"
                        large={true}
                        style={{ float: "right"}}
                        innerLabel={this.state.allowDifferentTimes ? "Consider all times" : "Only matching times"}
                        checked={this.state.allowDifferentTimes}
                        onChange={(e) => {
                            this.setState( { allowDifferentTimes: !this.state.allowDifferentTimes, personToJoin: "" } )
                            setTimeout(() => this.updateTargetCandidates(), 500)
                        }}/>
                    <Switch 
                        id="switch-schoolbound"
                        large={true}
                        style={{ float: "right"}}
                        innerLabel={this.state.schoolbound ? "Schoolbound" : "Homebound"}
                        checked={this.state.schoolbound}
                        onChange={(e) => {
                            this.setState( { schoolbound: !this.state.schoolbound, passengerToPlace: "", personToJoin: "" } )
                            setTimeout(() => this.updateTargetCandidates(), 500)
                        }}/>
                </div>
                <div style={flowStyle2} >
                    <FormGroup
                        helperText={undefined}
                        label="Passenger to place"
                        labelFor="input-passenger-to-place"
                        labelInfo={undefined} >
                        <Suggest
                            id="input-passenger-to-place"
                            placeholder="John Doe"
                            items={this.getCrPassengerCandidates()}
                            itemRenderer={(item, { handleClick, modifiers }) => this.renderItems(item, { handleClick, modifiers })}
                            autoComplete="off"
                            autoFocus={true}
                            itemListPredicate={(query, items) => items.filter((item) => this.filterItems(query, item))}
                            selectedItem={this.state.passengerToPlace}
                            inputValueRenderer={person => person === "" ? "" : person.firstName + " " + person.lastName + " (" + person.initials + ")"}
                            noResults={<MenuItem disabled={true} text="No results." />}
                            onItemSelect={(item) => {
                                this.setState({passengerToPlace: item})
                                const sourcePartyTime = this.calculateSourcePartyTime(item)
                                this.updateTargetCandidates(item, sourcePartyTime)
                            }} />
                        {this.state.passengerToPlace !== undefined && this.state.passengerToPlace !== "" ? "\u00A0" + this.state.sourcePartyTime : "" }
                    </FormGroup>
                    <FormGroup
                        helperText={undefined}
                        label="Person to join"
                        labelFor="input-person-to-join"
                        labelInfo={undefined} >
                        <Suggest
                            id="input-person-to-join"
                            placeholder="John Doe"
                            items={this.state.targetCandidates}
                            itemRenderer={(item, { handleClick, modifiers }) => this.renderItems(item, { handleClick, modifiers })}
                            autoComplete="off"
                            autoFocus={true}
                            itemListPredicate={(query, items) => items.filter((item) => this.filterItems(query, item))}
                            selectedItem={this.state.personToJoin}
                            inputValueRenderer={person => person === "" ? "" : person.firstName + " " + person.lastName + " (" + person.initials + ")"}
                            noResults={<MenuItem disabled={true} text="No results." />}
                            onItemSelect={(item) => {
                                this.setState({personToJoin: item})
                                this.calculateTargetPartyTime(item)
                            }} />
                        {this.state.personToJoin !== undefined && this.state.personToJoin !== "" ? "\u00A0" + this.state.targetPartyTime + "\u00A0" : "" }
                        {this.state.personToJoin !== undefined && this.state.personToJoin !== "" && this.state.sourcePartyTime !== this.state.targetPartyTime ? <Icon icon="issue" intent="warning"/> : ""}
                    </FormGroup>
                    <Button
                        icon="add"
                        text="Add ChangeRequest"
                        type="submit"
                        large={false}
                        intent="primary"
                        disabled={this.state.passengerToPlace === undefined || this.state.passengerToPlace === "" || this.state.personToJoin === undefined || this.state.personToJoin === ""}
                        onClick={() => {
                            let crs = this.state.changeRequests
                            let cr = {
                                person: this.state.passengerToPlace.initials,
                                dayNumber: this.props.dayPlan.dayOfWeekABCombo.uniqueNumber,
                                schoolbound: this.state.schoolbound,
                                sourcePartyDriver: this.state.passengerToPlace.driverInitials,
                                targetPartyDriver: this.state.personToJoin.driverInitials === undefined ? this.state.personToJoin.initials : this.state.personToJoin.driverInitials
                            }
                            crs.push(cr)
                            this.setState({ changeRequests: crs, passengerToPlace: '', personToJoin: '' })
                        }}/>
                </div>
                <div><hr/></div>
                <div style={flowStyle2}>
                    {this.state.changeRequests.map((cr, index) => {
                        return this.getCrListElement(cr, index)
                    })}
                </div>
                <div><hr/></div>
                <div style={flowStyle3}>
                    <Button
                        style={{width: "100px" }}
                        icon="delete"
                        text="Cancel"
                        onClick={() => {
                            this.setState({ changeRequests: [], passengerToPlace: '', personToJoin: '' })
                            this.props.closeCrDialog()
                        }}/>
                    <Button
                        style={{width: "100px" }}
                        icon="add"
                        text="Apply"
                        type="submit"
                        intent="primary"
                        disabled={this.state.changeRequests.length === 0}
                        onClick={() => {
                            this.props.applyChange(this.state.changeRequests)
                            this.setState({ changeRequests: [], passengerToPlace: '', personToJoin: '' })
                            this.props.closeCrDialog()
                            setTimeout(() => alert('The requested changes have successfully been applied.'), 500)
                        }}/>
                </div>
            </Dialog>
        )
    }

    timeToString(time) {
        let hh = Math.floor(time / 100)
        hh = hh < 10 ? "0" + hh : "" + hh
        let mm = time % 100
        mm = mm < 10 ? "0" + mm : "" + mm
        return (hh + ":" + mm + "h")
    }

    getCrListElement(cr, index) {
        return (
            <div key={index}>
                <b>{JSON.stringify(cr) + "\u00A0 \u00A0"}</b>
                <Icon 
                    style={{ cursor : "pointer", float: "right" }}
                    icon="remove"
                    intent="danger"
                    onClick={ () => {
                        let crs = this.state.changeRequests
                        crs.splice(index)
                        this.setState({changeRequests: crs})
                    }} />
            </div>
            )
    }
}


export default ChangeRequestDialog