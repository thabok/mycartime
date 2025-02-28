import { Icon, InputGroup, Tab, Tabs } from '@blueprintjs/core';
import React, { Component } from 'react';
import PartyList from './PartyList';

class DrivingPlan extends Component {

    constructor(props) {
        super()
        this.state = {
            selectedTabId: "tb-summary",
            crDialogOpen: false,
            crDayNumber: 1
        }
    }

    componentDidMount() {}

    //TODO: Update to new data structure
    processChangeRequests(changeRequests) {
        let plan = this.props.plan
        for (let crIndex=0; crIndex<changeRequests.length; crIndex++) {
            const changeRequest = changeRequests[crIndex]

            // find source and target party for current cr
            let sourceParty = null
            let targetParty = null
            let pts = plan.dayPlans[changeRequest.dayNumber].partyTuples
            for (let ptsIndex=0; ptsIndex<pts.length; ptsIndex++) {
                let party = changeRequest.schoolbound ? pts[ptsIndex].partyThere : pts[ptsIndex].partyBack
                if (party.driver.initials === changeRequest.sourcePartyDriver) {
                    sourceParty = party
                }
                if (party.driver.initials === changeRequest.targetPartyDriver) {
                    targetParty = party
                }
                if (sourceParty !== null && targetParty !== null) {
                    break
                }
            }

            // perform change
            for (let passengerIndex=0; passengerIndex<sourceParty.passengers.length; passengerIndex++) {
                const passengerInitials = sourceParty.passengers[passengerIndex].initials
                if (changeRequest.person === passengerInitials) {
                    targetParty.passengers.push(sourceParty.passengers.splice(passengerIndex, 1)[0])
                    break
                }
            }

        }
        // apply change
        this.props.updatePlan(plan)
    }

    getEditButton(dayNumber) {
        return(
            <td><Icon 
                style={{ cursor : "pointer" }}
                icon="edit"
                intent="primary"
                onClick={ () => {
                    this.setState({crDialogOpen: true, crDayNumber: dayNumber})
                }} /></td>
        )
    }

    getWeekA() {
        return this.getPartyTable([1, 2, 3, 4, 5])
    }

    getWeekB() {
        return this.getPartyTable([8, 9, 10, 11, 12])
    }

    getPartyTable(dayNumbers) {
        return (<tbody>
            {dayNumbers.map(dayNumber => (
                <tr key={dayNumber}>
                    <td><b>{this.getDayName(dayNumber)}</b></td>
                    <td><PartyList parties={this.props.drivingPlan.plan[dayNumber]['schoolbound_parties']} filterForPerson={this.state.filterForPerson} persons={this.props.drivingPlan.persons} /></td>
                    <td><PartyList parties={this.props.drivingPlan.plan[dayNumber]['homebound_parties']} filterForPerson={this.state.filterForPerson} persons={this.props.drivingPlan.persons} /></td>
                    {this.getEditButton(dayNumber)}
                </tr>
            ))}
        </tbody>)
    }

    getDayName(dayNumber) {
        switch (dayNumber) {
            case 1: return "Monday A"
            case 2: return "Tuesday A"
            case 3: return "Wednesday A"
            case 4: return "Thursday A"
            case 5: return "Friday A"
            case 8: return "Monday B"
            case 9: return "Tuesday B"
            case 10: return "Wednesday B"
            case 11: return "Thursday B"
            case 12: return "Friday B"
            default: return "Unknown"
        }
    }

    getLegend() {
        return (<tr><td colSpan={3} style={{"color": "#98FF98"}}><center><b>
            [*] Designated driver (=uncommon starting/leaving time)<br/>[**] Needs to drive alone (without passengers)
        </b></center></td></tr>)
    }

    getPlan(week_a, week_b) {
        return (<table className="bp3-html-table bp3-html-table-striped bp3-small">
            <tbody>
                <tr>
                    <th></th>
                    <th><center><b>Schoolbound</b></center></th>
                    <th><center><b>Homebound</b></center></th>
                </tr>
            </tbody>
            {/* <ChangeRequestDialog dayPlan={this.props.drivingPlan.plan[this.state.crDayNumber]} closeCrDialog={() => this.setState({crDialogOpen: false})} crDialogOpen={this.state.crDialogOpen} applyChange={(crList) => this.processChangeRequests(crList)}/> */}
            {week_a === true ? this.getWeekA() : null}
            {week_a && week_b ? <br/> : null}
            {week_b === true ? this.getWeekB() : null}
            {this.getLegend()}
        </table>)
    }

    getCompletePlan() {
        return (this.getPlan(true, true))
    }

    getPlanA() {
        return (this.getPlan(true, false))
    }

    getPlanB() {
        return (this.getPlan(false, true))
    }

    getSummaryHtml() {
        const drives = this.props.drivingPlan.summary.drives
        return (
            <ul>
                {Object.entries(drives).map(([key, value]) => (
                    <li key={key}>{`${key}: ${value}`}</li>
                ))}
            </ul>
        )
    }

    render() {
        return (
            <Tabs 
                id="driving-plan-tabs"
                onChange={(tab) => this.setState({selectedTabId: tab})}
                selectedTabId={this.state.selectedTabId}>
                <Tab id="tb-summary" title="Summary" panel={this.getSummaryHtml()}/>
                <Tab id="tb-week-a" title="Week A" panel={this.getPlanA()}/>
                <Tab id="tb-week-b" title="Week B" panel={this.getPlanB()}/>
                <Tab id="tb-complete" title="Complete Plan" panel={this.getCompletePlan()}/>
                <Tabs.Expander />
                <InputGroup 
                    id="input-filter-initials"
                    placeholder="filter by initials"
                    autoComplete="off"
                    leftIcon={<Icon icon="filter" intent={this.state.filterForPerson && this.state.filterForPerson !== '' ? "primary" : "none"} />}
                    onKeyPress={(e) => {
                        if (e.key === 'Enter') {
                            this.setState({filterForPerson: e.target.value})
                        }
                    }}/>
            </Tabs>
        );
    }
    
}

export default DrivingPlan;
