import React, { Component } from 'react';

class PartyList extends Component {

    constructor(props) {
        super()
        this.dayPlan = props.dayPlan
        this.state = {
            parties: this.sortParties(props.parties)
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
        if (party.problem_driver === true) {
            return '🚨'
        } else if (party.designated_driver === true) {
            return '*'
        } else if (party.lonely_driver === true) {
            return '**'
        } else {
            return ' '
        }
    }

    getPersonByInitials(initials) {
        for (let i = 0; i < this.dayPlan.people.length; i++) {
            if (this.dayPlan.people[i].initials === initials) {
                return this.dayPlan.people[i]
            }
        }
        return null
    }

    calculatePartyTime(party) {
        if (party.direction === 'schoolbound') {
            driver = this.getPersonByInitials(party.driver.initials)
            time = driver.schedule[party.day_index].startTime
            for (let i = 0; i < party.passengers.length; i++) {
                passenger = this.getPersonByInitials(party.passengers[i].initials)
                if (passenger.schedule[party.day_index].startTime < time) {
                    time = passenger.schedule[party.day_index].startTime
                }
            }
        } else { /* homebound */
            driver = this.getPersonByInitials(party.driver.initials)
            time = driver.schedule[party.day_index].endTime
            for (let i = 0; i < party.passengers.length; i++) {
                passenger = this.getPersonByInitials(party.passengers[i].initials)
                if (passenger.schedule[party.day_index].endTime > time) {
                    time = passenger.schedule[party.day_index].endTime
                }
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

}

export default PartyList;
