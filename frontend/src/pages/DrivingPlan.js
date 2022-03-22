import { Tab, Tabs, InputGroup, Icon } from '@blueprintjs/core';
import React, { Component } from 'react';
import ToupleList from './ToupleList'

class DrivingPlan extends Component {

    constructor(props) {
        super()
        this.state = {
            selectedTabId: "tb-summary"
        }
    }

    componentDidMount() {}

    getWeekA() {
        return (<tbody>
            <tr>
                <td><b>Monday (A)</b></td>
                <td><ToupleList touples={this.props.plan.dayPlans[1].partyTouples} schoolbound={true} filterForPerson={this.state.filterForPerson}/></td>
                <td><ToupleList touples={this.props.plan.dayPlans[1].partyTouples} schoolbound={false} filterForPerson={this.state.filterForPerson}/></td>
            </tr>
            <tr>
                <td><b>Tuesday (A)</b></td>
                <td><ToupleList touples={this.props.plan.dayPlans[2].partyTouples} schoolbound={true} filterForPerson={this.state.filterForPerson}/></td>
                <td><ToupleList touples={this.props.plan.dayPlans[2].partyTouples} schoolbound={false} filterForPerson={this.state.filterForPerson}/></td>
            </tr>
            <tr>
                <td><b>Wednesday (A)</b></td>
                <td><ToupleList touples={this.props.plan.dayPlans[3].partyTouples} schoolbound={true} filterForPerson={this.state.filterForPerson}/></td>
                <td><ToupleList touples={this.props.plan.dayPlans[3].partyTouples} schoolbound={false} filterForPerson={this.state.filterForPerson}/></td>
            </tr>
            <tr>
                <td><b>Thursday (A)</b></td>
                <td><ToupleList touples={this.props.plan.dayPlans[4].partyTouples} schoolbound={true} filterForPerson={this.state.filterForPerson}/></td>
                <td><ToupleList touples={this.props.plan.dayPlans[4].partyTouples} schoolbound={false} filterForPerson={this.state.filterForPerson}/></td>
            </tr>
            <tr>
                <td><b>Friday (A)</b></td>
                <td><ToupleList touples={this.props.plan.dayPlans[5].partyTouples} schoolbound={true} filterForPerson={this.state.filterForPerson}/></td>
                <td><ToupleList touples={this.props.plan.dayPlans[5].partyTouples} schoolbound={false} filterForPerson={this.state.filterForPerson}/></td>
            </tr>
        </tbody>)
    }

    getWeekB() {
        return (<tbody>
            <tr>
                <td><b>Monday (B)</b></td>
                <td><ToupleList touples={this.props.plan.dayPlans[8].partyTouples} schoolbound={true} filterForPerson={this.state.filterForPerson}/></td>
                <td><ToupleList touples={this.props.plan.dayPlans[8].partyTouples} schoolbound={false} filterForPerson={this.state.filterForPerson}/></td>
            </tr>
            <tr>
                <td><b>Tuesday (B)</b></td>
                <td><ToupleList touples={this.props.plan.dayPlans[9].partyTouples} schoolbound={true} filterForPerson={this.state.filterForPerson}/></td>
                <td><ToupleList touples={this.props.plan.dayPlans[9].partyTouples} schoolbound={false} filterForPerson={this.state.filterForPerson}/></td>
            </tr>
            <tr>
                <td><b>Wednesday (B)</b></td>
                <td><ToupleList touples={this.props.plan.dayPlans[10].partyTouples} schoolbound={true} filterForPerson={this.state.filterForPerson}/></td>
                <td><ToupleList touples={this.props.plan.dayPlans[10].partyTouples} schoolbound={false} filterForPerson={this.state.filterForPerson}/></td>
            </tr>
            <tr>
                <td><b>Thursday (B)</b></td>
                <td><ToupleList touples={this.props.plan.dayPlans[11].partyTouples} schoolbound={true} filterForPerson={this.state.filterForPerson}/></td>
                <td><ToupleList touples={this.props.plan.dayPlans[11].partyTouples} schoolbound={false} filterForPerson={this.state.filterForPerson}/></td>
            </tr>
            <tr>
                <td><b>Friday (B)</b></td>
                <td><ToupleList touples={this.props.plan.dayPlans[12].partyTouples} schoolbound={true} filterForPerson={this.state.filterForPerson}/></td>
                <td><ToupleList touples={this.props.plan.dayPlans[12].partyTouples} schoolbound={false} filterForPerson={this.state.filterForPerson}/></td>
            </tr>
        </tbody>)
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
                {this.getWeekA()}
                <tbody><tr><td colSpan={3}><center>----------------------------------------------------------------</center></td></tr></tbody>
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
