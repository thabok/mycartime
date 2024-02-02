import { Icon, InputGroup, Tab, Tabs } from '@blueprintjs/core';
import React, { Component } from 'react';
import ChangeRequestDialog from '../dialogs/ChangeRequestDialog';
import TupleList from './TupleList';

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
        return (<tbody>
            <tr>
                <td><b>Monday (A)</b></td>
                <td><TupleList tuples={this.props.plan.dayPlans[1].partyTuples} schoolbound={true} filterForPerson={this.state.filterForPerson} dayPlan={this.props.plan.dayPlans[1]} /></td>
                <td><TupleList tuples={this.props.plan.dayPlans[1].partyTuples} schoolbound={false} filterForPerson={this.state.filterForPerson} dayPlan={this.props.plan.dayPlans[1]} /></td>
                {this.getEditButton(1)}
            </tr>
            <tr>
                <td><b>Tuesday (A)</b></td>
                <td><TupleList tuples={this.props.plan.dayPlans[2].partyTuples} schoolbound={true} filterForPerson={this.state.filterForPerson} dayPlan={this.props.plan.dayPlans[2]} /></td>
                <td><TupleList tuples={this.props.plan.dayPlans[2].partyTuples} schoolbound={false} filterForPerson={this.state.filterForPerson} dayPlan={this.props.plan.dayPlans[2]} /></td>
                {this.getEditButton(2)}
            </tr>
            <tr>
                <td><b>Wednesday (A)</b></td>
                <td><TupleList tuples={this.props.plan.dayPlans[3].partyTuples} schoolbound={true} filterForPerson={this.state.filterForPerson} dayPlan={this.props.plan.dayPlans[3]} /></td>
                <td><TupleList tuples={this.props.plan.dayPlans[3].partyTuples} schoolbound={false} filterForPerson={this.state.filterForPerson} dayPlan={this.props.plan.dayPlans[3]} /></td>
                {this.getEditButton(3)}
            </tr>
            <tr>
                <td><b>Thursday (A)</b></td>
                <td><TupleList tuples={this.props.plan.dayPlans[4].partyTuples} schoolbound={true} filterForPerson={this.state.filterForPerson} dayPlan={this.props.plan.dayPlans[4]} /></td>
                <td><TupleList tuples={this.props.plan.dayPlans[4].partyTuples} schoolbound={false} filterForPerson={this.state.filterForPerson} dayPlan={this.props.plan.dayPlans[4]} /></td>
                {this.getEditButton(4)}
            </tr>
            <tr>
                <td><b>Friday (A)</b></td>
                <td><TupleList tuples={this.props.plan.dayPlans[5].partyTuples} schoolbound={true} filterForPerson={this.state.filterForPerson} dayPlan={this.props.plan.dayPlans[5]} /></td>
                <td><TupleList tuples={this.props.plan.dayPlans[5].partyTuples} schoolbound={false} filterForPerson={this.state.filterForPerson} dayPlan={this.props.plan.dayPlans[5]} /></td>
                {this.getEditButton(5)}
            </tr>
            {this.getLegend()}
        </tbody>)
    }

    getWeekB() {
        return (<tbody>
            <tr>
                <td><b>Monday (B)</b></td>
                <td><TupleList tuples={this.props.plan.dayPlans[8].partyTuples} schoolbound={true} filterForPerson={this.state.filterForPerson} dayPlan={this.props.plan.dayPlans[8]} /></td>
                <td><TupleList tuples={this.props.plan.dayPlans[8].partyTuples} schoolbound={false} filterForPerson={this.state.filterForPerson} dayPlan={this.props.plan.dayPlans[8]} /></td>
                {this.getEditButton(8)}
            </tr>
            <tr>
                <td><b>Tuesday (B)</b></td>
                <td><TupleList tuples={this.props.plan.dayPlans[9].partyTuples} schoolbound={true} filterForPerson={this.state.filterForPerson} dayPlan={this.props.plan.dayPlans[9]} /></td>
                <td><TupleList tuples={this.props.plan.dayPlans[9].partyTuples} schoolbound={false} filterForPerson={this.state.filterForPerson} dayPlan={this.props.plan.dayPlans[9]} /></td>
                {this.getEditButton(9)}
            </tr>
            <tr>
                <td><b>Wednesday (B)</b></td>
                <td><TupleList tuples={this.props.plan.dayPlans[10].partyTuples} schoolbound={true} filterForPerson={this.state.filterForPerson} dayPlan={this.props.plan.dayPlans[10]} /></td>
                <td><TupleList tuples={this.props.plan.dayPlans[10].partyTuples} schoolbound={false} filterForPerson={this.state.filterForPerson} dayPlan={this.props.plan.dayPlans[10]} /></td>
                {this.getEditButton(10)}
            </tr>
            <tr>
                <td><b>Thursday (B)</b></td>
                <td><TupleList tuples={this.props.plan.dayPlans[11].partyTuples} schoolbound={true} filterForPerson={this.state.filterForPerson} dayPlan={this.props.plan.dayPlans[11]} /></td>
                <td><TupleList tuples={this.props.plan.dayPlans[11].partyTuples} schoolbound={false} filterForPerson={this.state.filterForPerson} dayPlan={this.props.plan.dayPlans[11]} /></td>
                {this.getEditButton(11)}
            </tr>
            <tr>
                <td><b>Friday (B)</b></td>
                <td><TupleList tuples={this.props.plan.dayPlans[12].partyTuples} schoolbound={true} filterForPerson={this.state.filterForPerson} dayPlan={this.props.plan.dayPlans[12]} /></td>
                <td><TupleList tuples={this.props.plan.dayPlans[12].partyTuples} schoolbound={false} filterForPerson={this.state.filterForPerson} dayPlan={this.props.plan.dayPlans[12]} /></td>
                {this.getEditButton(12)}
            </tr>
            {this.getLegend()}
        </tbody>)
    }

    getLegend() {
        return (<tr><td colSpan={3} style={{"color": "#98FF98"}}><center><b>
            [*] Designated driver (must drive on given day)<br/>[**] Needs to drive alone (without passengers)
        </b></center></td></tr>)
    }

    getCompletePlan() {
        return (<table className="bp3-html-table bp3-html-table-striped bp3-small">
                <tbody>
                    <tr>
                        <th></th>
                        <th><center><b>Schoolbound</b></center></th>
                        <th><center><b>Homebound</b></center></th>
                    </tr>
                </tbody>
                <ChangeRequestDialog dayPlan={this.props.plan.dayPlans[this.state.crDayNumber]} closeCrDialog={() => this.setState({crDialogOpen: false})} crDialogOpen={this.state.crDialogOpen} applyChange={(crList) => this.processChangeRequests(crList)}/>
                {this.getWeekA()}
                {this.getWeekB()}
            </table>)
    }

    getPlanA() {
        return (<table className="bp3-html-table bp3-html-table-striped bp3-small">
                <tbody>
                    <tr>
                        <th></th>
                        <th><center><b>Schoolbound</b></center></th>
                        <th><center><b>Homebound</b></center></th>
                    </tr>
                </tbody>
                <ChangeRequestDialog dayPlan={this.props.plan.dayPlans[this.state.crDayNumber]} closeCrDialog={() => this.setState({crDialogOpen: false})} crDialogOpen={this.state.crDialogOpen} applyChange={(crList) => this.processChangeRequests(crList)}/>
                {this.getWeekA()}
            </table>)
    }

    getPlanB() {
        return (<table className="bp3-html-table bp3-html-table-striped bp3-small">
                <tbody>
                    <tr>
                        <th></th>
                        <th><center><b>Schoolbound</b></center></th>
                        <th><center><b>Homebound</b></center></th>
                    </tr>
                </tbody>
                <ChangeRequestDialog dayPlan={this.props.plan.dayPlans[this.state.crDayNumber]} closeCrDialog={() => this.setState({crDialogOpen: false})} crDialogOpen={this.state.crDialogOpen} applyChange={(crList) => this.processChangeRequests(crList)}/>
                {this.getWeekB()}
            </table>)
    }

    getSummaryHtml() {
        let lines = []
        try {
            lines = this.props.plan.summary.replaceAll("- ", "").split("\n")
        } catch (err) {
            console.error(err)
        }
        return (
            <ul>
                {lines.map((line, index) => line ? <li key={"sum_line_" + index}>{line}</li> : null)}
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
