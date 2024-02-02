import React, { Component } from 'react';

class TupleList extends Component {

    constructor(props) {
        super()
        this.dayPlan = props.dayPlan
        this.state = {
            parties: this.sortTuples(props.tuples, props.schoolbound)
        }
    }

    componentDidMount() { }

    render() {
        return (
            <ul>
                {this.state.parties.map((party, index) => {
                    if (this.props.filterForPerson && this.props.filterForPerson !== '') {
                        let found = party.driver.initials.toLowerCase().indexOf(this.props.filterForPerson.toLowerCase()) !== -1
                        if (!found) {
                            if (party.passengers) {
                                for (let i = 0; i < party.passengers.length; i++) {
                                    if (party.passengers[i].initials.toLowerCase().indexOf(this.props.filterForPerson.toLowerCase()) !== -1) {
                                        found = true
                                        break
                                    }
                                }
                            }
                        }
                        if (!found) return null
                    }
                    return (this.getListItem(party, index))
                })}
            </ul>
        );
    }

    getListItem(party, index) {
        let passengerStrings = []
        for (let i = 0; i < party.passengers.length; i++) {
            let p = party.passengers[i]
            passengerStrings.push(p.firstName + "\u00A0(" + p.initials + ")")
        }
        return (<li key={index}>
            [{this.timeToString(this.calculatePartyTime(party))}] <b>{this.getIndicator(party)}{party.driver.firstName + "\u00A0(" + party.driver.initials + ")"}</b> {(party.passengers.length > 0 ? " - " + passengerStrings.join(" - ") : "")}
        </li>)
    }

    getIndicator(party) {
        if (party.drivesDespiteCustomPrefs) {
            return '🚨'
        } else if (party.reason === 'DESIGNATED_DRIVER') {
            return '*'
        } else if (party.reason === 'LONELY_DRIVER') {
            return '**'
        } else {
            return ' '
        }
    }

    calculatePartyTime(party) {
        // refer to day plan map of person's times
        const map = party.isWayBack ? this.dayPlan.homeboundTimesByInitials : this.dayPlan.schoolboundTimesByInitials
        // set party time to driver time
        let time = map[party.driver.initials]
        // if there's a passenger time which is earlier (schoolbound) / later (homebound) -> adapt party time
        for (let i = 0; i < party.passengers.length; i++) {
            let passengerTime = map[party.passengers[i].initials]
            if ((!party.isWayBack && passengerTime < time) || (party.isWayBack && passengerTime > time)) {
                time = passengerTime
            }
        }
        return time
    }

    timeToString(time) {
        let hh = Math.floor(time / 100)
        hh = hh < 10 ? "0" + hh : "" + hh
        let mm = time % 100
        mm = mm < 10 ? "0" + mm : "" + mm
        return (hh + ":" + mm + "h")
    }

    sortTuples(unsortedTuples, schoolbound) {
        let parties = []
        for (let i = 0; i < unsortedTuples.length; i++) {
            const tuple = unsortedTuples[i]
            let party = null
            if (schoolbound) {
                party = tuple.partyThere
            } else {
                party = tuple.partyBack
            }
            party.isDesignatedDriver = tuple.isDesignatedDriver
            party.drivesDespiteCustomPrefs = tuple.drivesDespiteCustomPrefs
            parties.push(party)
        }
        parties.sort((a, b) => this.calculatePartyTime(a) < this.calculatePartyTime(b) ? -1 : 1)
        return parties
    }
}

export default TupleList;
